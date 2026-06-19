import json
import os
import sys
import warnings
import urllib.request
import geopandas as gpd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

COUNTRIES_FILE = 'countries.json'
OUTPUT_DIR = 'maps'
BUFFER_DEG = 0.15   # degrees; catches shared land borders

COLOR_FOCUS    = '#e74c3c'  # red   – the country itself
COLOR_NEIGHBOR = '#bdc3c7'  # gray – neighbors
COLOR_OCEAN    = '#d6eaf8'  # light blue – background

# ── name mapping: countries.json name → capitals dataset name ─────────────────
NAME_MAP = {
    'Antigua and Barb.':        'Antigua and Barbuda',
    'Bosnia and Herz.':         'Bosnia and Herzegovina',
    'Br. Indian Ocean Ter.':    'British Indian Ocean Territory',
    'British Virgin Is.':       'British Virgin Islands',
    'Cabo Verde':               'Cape Verde',
    'Cayman Is.':               'Cayman Islands',
    'Central African Rep.':     'Central African Republic',
    'Congo':                    'Congo Republic',
    'Cook Is.':                 'Cook Islands',
    "Côte d'Ivoire":            'Ivory Coast',
    'Czechia':                  'Czech Republic',
    'Dem. Rep. Congo':          'Congo Democratic Republic',
    'Dominican Rep.':           'Dominican Republic',
    'Eq. Guinea':               'Equatorial Guinea',
    'Faeroe Is.':               'Faroe Islands',
    'Falkland Is.':             'Falkland Islands',
    'Fr. Polynesia':            'French Polynesia',
    'Fr. S. Antarctic Lands':   'French Southern Territories',
    'Heard I. and McDonald Is.':'Heard Island and McDonald Islands',
    'Macao':                    'Macao',
    'Marshall Is.':             'Marshall Islands',
    'N. Mariana Is.':           'Northern Mariana Islands',
    'North Korea':              'Korea North',
    'Palestine':                'Palestinian Territory',
    'Pitcairn Is.':             'Pitcairn',
    'Saint Helena':             'Saint Helena Ascension and Tristan da Cunha',
    'Solomon Is.':              'Solomon Islands',
    'South Korea':              'Korea South',
    'São Tomé and Principe':    'Sao Tome and Principe',
    'St-Barthélemy':            'Saint Barthelemy',
    'St-Martin':                'Saint Martin',
    'St. Kitts and Nevis':      'Saint Kitts and Nevis',
    'St. Pierre and Miquelon':  'Saint Pierre and Miquelon',
    'St. Vin. and Gren.':       'Saint Vincent and the Grenadines',
    'Turks and Caicos Is.':     'Turks and Caicos Islands',
    'U.S. Virgin Is.':          'Virgin Islands',
    'United States of America': 'United States',
    'W. Sahara':                'Western Sahara',
    'Wallis and Futuna Is.':    'Wallis and Futuna',
    'eSwatini':                 'Swaziland',
    'Macedonia':                'Macedonia',
}

# hardcoded fallbacks for countries not in the dataset at all
HARDCODED = {
    'Kosovo':       ('Pristina',    21.17,  42.67),
    'S. Sudan':     ('Juba',        31.57,   4.85),
    'Sint Maarten': ('Philipsburg', -63.05, 18.03),
    'Curaçao':      ('Willemstad',  -68.93, 12.11),
    'N. Cyprus':    ('North Nicosia', 33.36, 35.18),
    'Somaliland':   ('Hargeisa',    44.07,   9.56),
    'Åland':        ('Mariehamn',   19.94,  60.10),
    'Nauru':        ('Yaren',       166.92,  -0.55),
}

# ── fetch capitals ─────────────────────────────────────────────────────────────
print('Fetching capitals …')
capitals = {}   # our-country-name → {'city': str, 'lon': float, 'lat': float}
try:
    url = 'https://raw.githubusercontent.com/Stefie/geojson-world/master/capitals.geojson'
    with urllib.request.urlopen(url, timeout=10) as r:
        cap_raw = json.loads(r.read())
    dataset = {}
    for feat in cap_raw['features']:
        p = feat['properties']
        if p.get('country') and p.get('city'):
            lon, lat = feat['geometry']['coordinates']
            dataset[p['country']] = {'city': p['city'], 'lon': lon, 'lat': lat}

    with open(COUNTRIES_FILE) as f:
        _tmp = json.load(f)
    for feat in _tmp['features']:
        name = feat['properties']['name']
        key  = NAME_MAP.get(name, name)          # translate if needed
        if key in dataset:
            capitals[name] = dataset[key]
        elif name in HARDCODED:
            city, lon, lat = HARDCODED[name]
            capitals[name] = {'city': city, 'lon': lon, 'lat': lat}
    print(f'  loaded {len(capitals)} capitals')
except Exception as e:
    print(f'  warning: could not fetch capitals ({e})')

# ── load ──────────────────────────────────────────────────────────────────────
with open(COUNTRIES_FILE) as f:
    data = json.load(f)

gdf = gpd.GeoDataFrame.from_features(data['features'])
gdf = gdf.set_crs('EPSG:4326').reset_index(drop=True)
# drop countries with null/empty geometry (e.g. Vatican in this dataset)
gdf = gdf[~(gdf.geometry.is_empty | gdf.geometry.isna())].reset_index(drop=True)

# ── compute neighbors ─────────────────────────────────────────────────────────
print('Computing neighbors …')
with warnings.catch_warnings():
    warnings.simplefilter('ignore')
    buffered = gdf.geometry.buffer(BUFFER_DEG)

neighbor_map = {}
for i, row in gdf.iterrows():
    nbrs = []
    for j, row2 in gdf.iterrows():
        if i == j:
            continue
        if buffered[i].intersects(gdf.geometry[j]):
            nbrs.append(row2['name'])
    neighbor_map[row['name']] = nbrs

# ── render ────────────────────────────────────────────────────────────────────
os.makedirs(OUTPUT_DIR, exist_ok=True)
total = len(gdf)

for idx, (_, row) in enumerate(gdf.iterrows(), 1):
    country = row['name']
    nbr_names = neighbor_map[country]

    sys.stdout.write(f'\r[{idx}/{total}] {country:<40}')
    sys.stdout.flush()

    focus_mask = gdf['name'] == country
    nbr_mask   = gdf['name'].isin(nbr_names)

    # ── extent: centered on the country itself, small border padding ──────────
    minx, miny, maxx, maxy = gdf[focus_mask].total_bounds
    w, h = maxx - minx, maxy - miny
    pad = max(w, h) * 0.12 + 0.8   # small padding so borders are visible

    xlim = (minx - pad, maxx + pad)
    ylim = (miny - pad, maxy + pad)

    fig, ax = plt.subplots(figsize=(12, 7))
    fig.patch.set_facecolor(COLOR_OCEAN)
    ax.set_facecolor(COLOR_OCEAN)

    # draw neighbors first (they'll be clipped by the axes limits)
    if nbr_mask.any():
        gdf[nbr_mask].plot(ax=ax, color=COLOR_NEIGHBOR, edgecolor='#ffffff', linewidth=0.5)
    # draw the country on top so it's never obscured
    gdf[focus_mask].plot(ax=ax, color=COLOR_FOCUS, edgecolor='#ffffff', linewidth=0.6)

    # ── neighbor labels ───────────────────────────────────────────────────────
    for _, nb in gdf[nbr_mask].iterrows():
        pt = nb.geometry.representative_point()
        # only label if the point falls inside our view
        if xlim[0] <= pt.x <= xlim[1] and ylim[0] <= pt.y <= ylim[1]:
            ax.text(
                pt.x, pt.y, nb['name'],
                fontsize=7, ha='center', va='center', color='#1a252f',
                fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.2', facecolor='white',
                          alpha=0.6, edgecolor='none'),
                clip_on=True,
            )

    # ── capital marker ────────────────────────────────────────────────────────
    cap = capitals.get(country)
    if cap:
        cx, cy = cap['lon'], cap['lat']
        ax.plot(cx, cy, marker='o', markersize=5, color='white',
                markeredgecolor='#1a252f', markeredgewidth=0.8, zorder=5)
        ax.text(cx + (maxx - minx) * 0.015 + 0.1, cy, cap['city'],
                fontsize=7.5, va='center', color='white', fontweight='bold',
                clip_on=True, zorder=5)

    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.set_axis_off()
    ax.set_title(country, fontsize=17, fontweight='bold', pad=10, color='#1a252f')

    legend_handles = [
        Patch(facecolor=COLOR_FOCUS,    edgecolor='#888', label=country),
        Patch(facecolor=COLOR_NEIGHBOR, edgecolor='#888', label='Neighbors'),
    ]
    ax.legend(handles=legend_handles, loc='lower left', fontsize=9,
              framealpha=0.85, edgecolor='#cccccc')

    plt.tight_layout(pad=0.4)
    safe_name = country.replace('/', '_').replace(' ', '_')
    fig.savefig(f'{OUTPUT_DIR}/{safe_name}.svg', format='svg', bbox_inches='tight')
    plt.close(fig)

print(f'\nDone – {total} SVGs saved to ./{OUTPUT_DIR}/')
