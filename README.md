# Territory control via liveuamap

**TL;DR:** Download [territory.csv](territory.csv) for daily Russian control of
Ukrainian territory figures.

Areas already occupied pre-2022 (Crimea, "DNR", "LNR") are included in
computations.

### Preparation
Install dependencies via `pip install -r requirements.txt`.

For map visualizations in the jupyter notebook, install `ipyleaflet` and
`ipywidgets`.

### Scraping the data
Run `python scrape.py`. Scraped items will appear as `.json` in the `data/`
folder.

### Computing territory
Run `python update_csv.py`. The `territory.csv` file is automatically updated
once a day via GitHub actions.

### Analysis

See the accompanying ipython jupyter notebook:
[liveuamap_territory.ipynb](liveuamap_territory.ipynb)

![liveuamap_area_total](liveuamap_area_total.svg)
![liveuamap_area_net](liveuamap_area_net.svg)
![liveuamap_nzz_area_comparison_total](liveuamap_nzz_area_comparison_total.svg)
![comparison_liveuamap_nzz_median](comparison_liveuamap_nzz_median.svg)
![comparison_territory_net_missiles_eor](comparison_territory_net_missiles_eor.svg)
![comparison_territory_total_missiles_eor](comparison_territory_total_missiles_eor.svg)
