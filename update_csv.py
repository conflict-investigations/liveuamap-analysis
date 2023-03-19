import json
import geopandas as gpd
import numpy as np
import pandas as pd
import os
from datetime import datetime
from multiprocessing.pool import ThreadPool
from shapely.geometry import Polygon, MultiPolygon, shape
from shapely import GEOSException

PARALLEL_PROCESSES = 16
EXPORT_FILE = 'liveuamap.csv'

try:
    previous = pd.read_csv(EXPORT_FILE, parse_dates=True)
    previous.index = pd.to_datetime(previous.date.values).to_pydatetime()
    previous = previous.drop(columns=['date'])
except FileNotFoundError:
    previous = pd.DataFrame(columns=['area'])

def load_json(filename):
    with open('data/' + filename, 'r') as f:
        return json.load(f)
def get_coords(points):
    shapes = []
    if type(points[0]) is dict:
        coords = []
        for p in points:
            coords.append([p.get('lat'), p.get('lng')])
        shapes.append(coords)
        return shapes
    for p in points:
        shapes.append(np.column_stack([p[1::2], p[::2]]))
    return shapes


# Boundaries of Ukraine
ua_outline = gpd.read_file('stanford.geojson')
# CRS already set
# ua_outline = ua_outline.set_crs('EPSG:4326')
outline = ua_outline['geometry'].iloc[0]

def extract_shapes(f):

    shape_dicts = []

    for field_id, field_dict in f['fields'].items():

        # Recaptured areas are not Russian-controlled, to skip them
        if field_dict.get('name') == 'Ukraine recaptured':
            continue
        # Same for "Territories, liberated from Russian forces"
        if 'liberated from Russian' in field_dict.get('description'):
            continue

        c = get_coords(field_dict['points'])

        if len(c) == 0:
            # Simple polygon
            if len(c[0] >= 3):
                # Only at least 3 points can form a valid polygon, prevent errors later on
                polygon = Polygon(c[0])
        else:
            # Multiple polygons, to be combined
            polygon_list = []
            for coord_pair in c:
                if len(coord_pair) >= 4:
                    # Prevent 'ValueError: A linearring requires at least 4 coordinates.'
                    polygon_list.append(Polygon(coord_pair))
            polygon = MultiPolygon(polygon_list)

        shape_dict = dict(id=field_id, name=field_dict['name'], geometry=polygon)
        shape_dicts.append(shape_dict)

    return shape_dicts

def process_item(args):
    idx, filename = args
    print(f"(Processing {idx}", end='\r')

    f = load_json(filename)
    id_ = filename.split('.json')[0]
    date = datetime.fromtimestamp(int(id_))

    shape_dicts = extract_shapes(f)

    ua_territory = gpd.GeoDataFrame(shape_dicts)
    ua_territory = ua_territory.set_crs('EPSG:4326')

    # Resolve some issues with data
    ua_territory['geometry'] = ua_territory.geometry.buffer(0)

    try:
        ua_territory['intersects'] = ua_territory['geometry'].intersects(outline)
    except GEOSException as e:
        print(f"filename: {filename}, Error: {e}")
        # In case of errors, show the affected area
        print(ua_territory)
        ua_territory.plot()
        raise

    # Drop areas entirely outside Ukrainian bounds
    # Prevents an error message when running .intersection() next
    ua_territory = ua_territory[ua_territory['intersects'] == True]
    # Reduce controlled areas to inside Ukrainian bounds
    try:
        ua_territory['geometry'] = ua_territory['geometry'].intersection(outline)
    except GEOSException as e:
        print(f"filename: {filename}, Error: {e}")
        # In case of errors, show the affected area
        print(ua_territory)
        ua_territory.plot()
        raise

    joined = ua_territory.dissolve(by=None).iloc[0]

    # Drop unneeded boolean column
    ua_territory = ua_territory.drop(['intersects'], axis=1)

    ua_territory = ua_territory.to_crs({'proj': 'cea'})
    ua_territory['area'] = ua_territory['geometry'].area / 10**6

    area = ua_territory['area'].sum()

    return [id_, date, area, joined]


processed = []
files = sorted(os.listdir('data'))
to_process = []
for filename in files:
    if not datetime.fromtimestamp(int(filename.split('.json')[0])) in previous.index:
        to_process.append(filename)

def dispatch(items):
    print(f"Processing all {len(items)} items...")
    return list(ThreadPool(
        PARALLEL_PROCESSES).imap_unordered(process_item, enumerate(items, 1)))


# XXX this may be slow, takes about 2min on first run
processed = dispatch(to_process[:])

df = pd.DataFrame(processed, columns=['id', 'date', 'area', 'features'])
df = df.drop(['id'], axis=1)
df = df.sort_values(by='date', ascending = True)
df = df.set_index('date')

df['area'] = df['area'].astype('float')
# Calculate change to previous day which translates to daily gains/losses
df['change'] = df['area'].diff()

adjusted = df.copy()
# Fix outliers
adjusted['2022-05-15':'2022-05-19'] = adjusted[adjusted.index == '2022-05-14'].values
adjusted.loc[adjusted.index == '2022-08-25'] = adjusted[adjusted.index == '2022-08-24'].values
# Recompute changed area
adjusted['change'] = adjusted['area'].diff()

combined = pd.DataFrame(pd.concat([previous['area'], adjusted['area']]))
combined.index.name = 'date'

# Save all computed area figures to .csv file
combined['area'].to_csv(EXPORT_FILE)
