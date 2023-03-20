import datetime
import json
import os
import pandas as pd
import pathlib

import requests

BASE_URL = 'https://liveuamap.com/ajax/do'
USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'  # noqa

DATA_FOLDER = 'data'
EXPORT_FILE = 'territory.csv'

# Already start at 2022-02-20 to account for inaccuracies on 2022-02-24
start = datetime.datetime(2022, 2, 20)
end = datetime.datetime.today()
dates = [start + datetime.timedelta(days=x)
         for x in range(0, (end-start).days + 1)]

def save_to_file(items, filename):
    with open(filename, 'w') as f:
        json.dump(items, f, ensure_ascii=False, indent=2)

def scrape_json(timestamp):
    params = {
        'act': 'getFields',
        'time': timestamp,
        'resid': 0,
        'lang': 'en',
        'isUserReg': 0
    }
    headers = {
        'User-Agent': USER_AGENT,
    }
    response = requests.get(url=BASE_URL, headers=headers, params=params)

    return response.json()


# Ensure 'items' dir exists
pathlib.Path(DATA_FOLDER).mkdir(parents=True, exist_ok=True)

try:
    previous = pd.read_csv(EXPORT_FILE, parse_dates=True)
    previous.index = pd.to_datetime(previous.date.values).to_pydatetime()
    previous = previous.drop(columns=['date'])
except FileNotFoundError:
    previous = pd.DataFrame(columns=['area'])

to_process = []
for date in dates:
    if date not in previous.index:
        to_process.append(str(int(datetime.datetime.timestamp(date))))

def scrape_items(items):

    def id_exists(id_):
        if os.path.isfile(DATA_FOLDER + '/' + id_ + '.json'):
            return True

    ids = list(filter(
        lambda x: not id_exists(x), [p for p in items]
    ))

    def scrape_content(id_):
        entry = scrape_json(id_)
        save_to_file(entry, DATA_FOLDER + '/' + id_ + '.json')
        entry['id'] = id_
        return entry

    if len(ids) == 0:
        print("No new items")
        return

    print(f"Scraping {len(ids)} new items...")

    return list(map(scrape_content, ids))


scrape_items(to_process)
