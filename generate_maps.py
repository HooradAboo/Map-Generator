import json
import os
import sys
import warnings
import urllib.request
import geopandas as gpd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# ── paths ─────────────────────────────────────────────────────────────────────
COUNTRIES_FILE  = 'countries.json'
CAPITALS_CACHE  = 'capitals_cache.json'
NEIGHBORS_CACHE = 'neighbors_cache.json'
OUTPUT_DIR      = 'maps'

# ── geometry ──────────────────────────────────────────────────────────────────
BUFFER_DEG      = 0.15    # catches shared land borders
PAD_FACTOR      = 0.12    # fraction of max(w,h) added as padding
PAD_MIN         = 0.8     # minimum padding in degrees

# ── colors ────────────────────────────────────────────────────────────────────
COLOR_NEIGHBOR  = '#bdc3c7'   # neighbors
COLOR_OCEAN     = '#d6eaf8'   # background
COLOR_LABEL     = '#1a252f'   # capital text
COLOR_NBR_LABEL = '#d6eaf8'   # neighbor country name labels
COLOR_CAP_DOT   = '#d6eaf8'   # capital marker fill

CONTINENT_COLORS = {
    'Africa':        '#E67E22',  # warm orange
    'Asia':          '#9B59B6',  # amethyst purple
    'Europe':        '#2980B9',  # steel blue
    'North America': '#27AE60',  # emerald green
    'South America': '#F1C40F',  # golden yellow
    'Oceania':       '#E91E8C',  # hot pink
    'Antarctica':    '#95A5A6',  # silver grey
    'Other':         '#7F8C8D',  # dark grey fallback
}

COUNTRY_CONTINENT = {
    # Africa
    'Algeria': 'Africa', 'Angola': 'Africa', 'Benin': 'Africa',
    'Botswana': 'Africa', 'Burkina Faso': 'Africa', 'Burundi': 'Africa',
    'Cabo Verde': 'Africa', 'Cameroon': 'Africa', 'Central African Rep.': 'Africa',
    'Chad': 'Africa', 'Comoros': 'Africa', 'Congo': 'Africa',
    "Côte d'Ivoire": 'Africa', 'Dem. Rep. Congo': 'Africa', 'Djibouti': 'Africa',
    'Egypt': 'Africa', 'Eq. Guinea': 'Africa', 'Eritrea': 'Africa',
    'Ethiopia': 'Africa', 'Gabon': 'Africa', 'Gambia': 'Africa',
    'Ghana': 'Africa', 'Guinea': 'Africa', 'Guinea-Bissau': 'Africa',
    'Kenya': 'Africa', 'Lesotho': 'Africa', 'Liberia': 'Africa',
    'Libya': 'Africa', 'Madagascar': 'Africa', 'Malawi': 'Africa',
    'Mali': 'Africa', 'Mauritania': 'Africa', 'Mauritius': 'Africa',
    'Morocco': 'Africa', 'Mozambique': 'Africa', 'Namibia': 'Africa',
    'Niger': 'Africa', 'Nigeria': 'Africa', 'Rwanda': 'Africa',
    'Saint Helena': 'Africa', 'São Tomé and Principe': 'Africa',
    'Senegal': 'Africa', 'Seychelles': 'Africa', 'Sierra Leone': 'Africa',
    'Somalia': 'Africa', 'Somaliland': 'Africa', 'South Africa': 'Africa',
    'S. Sudan': 'Africa', 'Sudan': 'Africa', 'Tanzania': 'Africa',
    'Togo': 'Africa', 'Tunisia': 'Africa', 'Uganda': 'Africa',
    'W. Sahara': 'Africa', 'Zambia': 'Africa', 'Zimbabwe': 'Africa',
    'eSwatini': 'Africa', 'Br. Indian Ocean Ter.': 'Africa',

    # Asia
    'Afghanistan': 'Asia', 'Armenia': 'Asia', 'Azerbaijan': 'Asia',
    'Bahrain': 'Asia', 'Bangladesh': 'Asia', 'Bhutan': 'Asia',
    'Brunei': 'Asia', 'Cambodia': 'Asia', 'China': 'Asia',
    'Georgia': 'Asia', 'Hong Kong': 'Asia', 'India': 'Asia',
    'Indonesia': 'Asia', 'Iran': 'Asia', 'Iraq': 'Asia',
    'Israel': 'Asia', 'Japan': 'Asia', 'Jordan': 'Asia',
    'Kazakhstan': 'Asia', 'Kuwait': 'Asia', 'Kyrgyzstan': 'Asia',
    'Laos': 'Asia', 'Lebanon': 'Asia', 'Macao': 'Asia',
    'Malaysia': 'Asia', 'Maldives': 'Asia', 'Mongolia': 'Asia',
    'Myanmar': 'Asia', 'N. Cyprus': 'Asia', 'Nepal': 'Asia',
    'North Korea': 'Asia', 'Oman': 'Asia', 'Pakistan': 'Asia',
    'Palestine': 'Asia', 'Philippines': 'Asia', 'Qatar': 'Asia',
    'Saudi Arabia': 'Asia', 'Singapore': 'Asia', 'South Korea': 'Asia',
    'Sri Lanka': 'Asia', 'Syria': 'Asia', 'Taiwan': 'Asia',
    'Tajikistan': 'Asia', 'Thailand': 'Asia', 'Timor-Leste': 'Asia',
    'Turkey': 'Asia', 'Turkmenistan': 'Asia', 'United Arab Emirates': 'Asia',
    'Uzbekistan': 'Asia', 'Vietnam': 'Asia', 'Yemen': 'Asia',
    'Cyprus': 'Asia', 'Baikonur': 'Asia', 'Siachen Glacier': 'Asia',
    'Scarborough Reef': 'Asia', 'Spratly Is.': 'Asia',

    # Europe
    'Albania': 'Europe', 'Andorra': 'Europe', 'Austria': 'Europe',
    'Belarus': 'Europe', 'Belgium': 'Europe', 'Bosnia and Herz.': 'Europe',
    'Bulgaria': 'Europe', 'Croatia': 'Europe', 'Czechia': 'Europe',
    'Denmark': 'Europe', 'Estonia': 'Europe', 'Faeroe Is.': 'Europe',
    'Finland': 'Europe', 'France': 'Europe', 'Germany': 'Europe',
    'Gibraltar': 'Europe', 'Greece': 'Europe', 'Guernsey': 'Europe',
    'Hungary': 'Europe', 'Iceland': 'Europe', 'Ireland': 'Europe',
    'Isle of Man': 'Europe', 'Italy': 'Europe', 'Jersey': 'Europe',
    'Kosovo': 'Europe', 'Latvia': 'Europe', 'Liechtenstein': 'Europe',
    'Lithuania': 'Europe', 'Luxembourg': 'Europe', 'Macedonia': 'Europe',
    'Malta': 'Europe', 'Moldova': 'Europe', 'Monaco': 'Europe',
    'Montenegro': 'Europe', 'Netherlands': 'Europe', 'Norway': 'Europe',
    'Poland': 'Europe', 'Portugal': 'Europe', 'Romania': 'Europe',
    'Russia': 'Europe', 'San Marino': 'Europe', 'Serbia': 'Europe',
    'Slovakia': 'Europe', 'Slovenia': 'Europe', 'Spain': 'Europe',
    'Sweden': 'Europe', 'Switzerland': 'Europe', 'Ukraine': 'Europe',
    'United Kingdom': 'Europe', 'Vatican': 'Europe', 'Åland': 'Europe',
    'Akrotiri': 'Europe', 'Dhekelia': 'Europe',
    'Cyprus U.N. Buffer Zone': 'Europe',

    # North America
    'Anguilla': 'North America', 'Antigua and Barb.': 'North America',
    'Aruba': 'North America', 'Bahamas': 'North America',
    'Barbados': 'North America', 'Belize': 'North America',
    'Bermuda': 'North America', 'British Virgin Is.': 'North America',
    'Canada': 'North America', 'Cayman Is.': 'North America',
    'Clipperton I.': 'North America', 'Cuba': 'North America',
    'Curaçao': 'North America', 'Dominica': 'North America',
    'Dominican Rep.': 'North America', 'El Salvador': 'North America',
    'Greenland': 'North America', 'Grenada': 'North America',
    'Guatemala': 'North America', 'Haiti': 'North America',
    'Honduras': 'North America', 'Jamaica': 'North America',
    'Mexico': 'North America', 'Montserrat': 'North America',
    'Nicaragua': 'North America', 'Panama': 'North America',
    'Puerto Rico': 'North America', 'Sint Maarten': 'North America',
    'St-Barthélemy': 'North America', 'St-Martin': 'North America',
    'St. Kitts and Nevis': 'North America', 'St. Pierre and Miquelon': 'North America',
    'St. Vin. and Gren.': 'North America', 'Trinidad and Tobago': 'North America',
    'Turks and Caicos Is.': 'North America', 'U.S. Minor Outlying Is.': 'North America',
    'U.S. Virgin Is.': 'North America', 'USNB Guantanamo Bay': 'North America',
    'United States of America': 'North America', 'Bajo Nuevo Bank': 'North America',
    'Serranilla Bank': 'North America',

    # South America
    'Argentina': 'South America', 'Bolivia': 'South America',
    'Brazil': 'South America', 'Chile': 'South America',
    'Colombia': 'South America', 'Ecuador': 'South America',
    'Falkland Is.': 'South America', 'Guyana': 'South America',
    'Paraguay': 'South America', 'Peru': 'South America',
    'S. Geo. and the Is.': 'South America', 'Suriname': 'South America',
    'Uruguay': 'South America', 'Venezuela': 'South America',

    # Oceania
    'American Samoa': 'Oceania', 'Ashmore and Cartier Is.': 'Oceania',
    'Australia': 'Oceania', 'Cook Is.': 'Oceania', 'Coral Sea Is.': 'Oceania',
    'Fiji': 'Oceania', 'Fr. Polynesia': 'Oceania', 'Guam': 'Oceania',
    'Heard I. and McDonald Is.': 'Oceania', 'Indian Ocean Ter.': 'Oceania',
    'Kiribati': 'Oceania', 'Marshall Is.': 'Oceania', 'Micronesia': 'Oceania',
    'Nauru': 'Oceania', 'New Caledonia': 'Oceania', 'New Zealand': 'Oceania',
    'Niue': 'Oceania', 'Norfolk Island': 'Oceania', 'N. Mariana Is.': 'Oceania',
    'Palau': 'Oceania', 'Papua New Guinea': 'Oceania', 'Pitcairn Is.': 'Oceania',
    'Samoa': 'Oceania', 'Solomon Is.': 'Oceania', 'Tonga': 'Oceania',
    'Tuvalu': 'Oceania', 'Vanuatu': 'Oceania', 'Wallis and Futuna Is.': 'Oceania',

    # Antarctica
    'Antarctica': 'Antarctica', 'Fr. S. Antarctic Lands': 'Antarctica',
}

# ── figure ────────────────────────────────────────────────────────────────────
FIG_SIZE          = (18, 8)
TITLE_FONTSIZE    = 17
NEIGHBOR_FONTSIZE = 30
CAPITAL_FONTSIZE  = 25
LEGEND_FONTSIZE   = 9
BORDER_LINEWIDTH  = 0.5
FOCUS_LINEWIDTH   = 0.6
CAP_MARKERSIZE    = 15
CAP_EDGE_WIDTH    = 0.8
CAP_LABEL_OFFSET  = 0.1   # degrees; horizontal nudge on the capital label

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

# ── CLI: optional list of country names to render ─────────────────────────────
target_countries = sys.argv[1:] if len(sys.argv) > 1 else []

# ── fetch / cache capitals ────────────────────────────────────────────────────
capitals = {}   # our-country-name → {'city': str, 'lon': float, 'lat': float}

if os.path.exists(CAPITALS_CACHE):
    print(f'Loading capitals from cache ({CAPITALS_CACHE}) …')
    with open(CAPITALS_CACHE) as f:
        capitals = json.load(f)
else:
    print('Fetching capitals …')
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
            key  = NAME_MAP.get(name, name)
            if key in dataset:
                capitals[name] = dataset[key]
            elif name in HARDCODED:
                city, lon, lat = HARDCODED[name]
                capitals[name] = {'city': city, 'lon': lon, 'lat': lat}

        with open(CAPITALS_CACHE, 'w') as f:
            json.dump(capitals, f)
        print(f'  loaded {len(capitals)} capitals (cached to {CAPITALS_CACHE})')
    except Exception as e:
        print(f'  warning: could not fetch capitals ({e})')

# ── load geodata ───────────────────────────────────────────────────────────────
with open(COUNTRIES_FILE) as f:
    data = json.load(f)

gdf = gpd.GeoDataFrame.from_features(data['features'])
gdf = gdf.set_crs('EPSG:4326').reset_index(drop=True)
gdf = gdf[~(gdf.geometry.is_empty | gdf.geometry.isna())].reset_index(drop=True)

# ── filter to requested countries if provided ─────────────────────────────────
if target_countries:
    missing = [c for c in target_countries if c not in gdf['name'].values]
    if missing:
        print(f'Unknown country name(s): {", ".join(missing)}')
        sys.exit(1)
    render_gdf = gdf[gdf['name'].isin(target_countries)]
else:
    render_gdf = gdf

# ── compute / cache neighbors ──────────────────────────────────────────────────
if os.path.exists(NEIGHBORS_CACHE):
    print(f'Loading neighbors from cache ({NEIGHBORS_CACHE}) …')
    with open(NEIGHBORS_CACHE) as f:
        neighbor_map = json.load(f)
else:
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

    with open(NEIGHBORS_CACHE, 'w') as f:
        json.dump(neighbor_map, f)
    print(f'  computed {len(neighbor_map)} entries (cached to {NEIGHBORS_CACHE})')

# ── render ─────────────────────────────────────────────────────────────────────
os.makedirs(OUTPUT_DIR, exist_ok=True)
total = len(render_gdf)

for idx, (_, row) in enumerate(render_gdf.iterrows(), 1):
    country = row['name']
    nbr_names = neighbor_map[country]

    sys.stdout.write(f'\r[{idx}/{total}] {country:<40}')
    sys.stdout.flush()

    focus_mask = gdf['name'] == country
    nbr_mask   = gdf['name'].isin(nbr_names)

    minx, miny, maxx, maxy = gdf[focus_mask].total_bounds
    w, h = maxx - minx, maxy - miny
    cx, cy = (minx + maxx) / 2, (miny + maxy) / 2
    target_ratio = FIG_SIZE[0] / FIG_SIZE[1]

    fh = h / 0.90
    fw = fh * target_ratio
    if w / fw >= 0.70:
        fw = w / 0.70
        fh = fw / target_ratio

    xlim = (cx - fw / 2, cx + fw / 2)
    ylim = (cy - fh / 2, cy + fh / 2)

    continent = COUNTRY_CONTINENT.get(country, 'Other')
    color_focus = CONTINENT_COLORS[continent]

    fig, ax = plt.subplots(figsize=FIG_SIZE)
    fig.patch.set_facecolor(COLOR_OCEAN)
    ax.set_facecolor(COLOR_OCEAN)

    gdf[~focus_mask].plot(ax=ax, color=COLOR_NEIGHBOR, edgecolor='#ffffff', linewidth=BORDER_LINEWIDTH)
    gdf[focus_mask].plot(ax=ax, color=color_focus, edgecolor='#ffffff', linewidth=FOCUS_LINEWIDTH)

    for _, nb in gdf[~focus_mask].iterrows():
        pt = nb.geometry.representative_point()
        if xlim[0] <= pt.x <= xlim[1] and ylim[0] <= pt.y <= ylim[1]:
            ax.text(
                pt.x, pt.y, nb['name'],
                fontsize=NEIGHBOR_FONTSIZE, ha='center', va='center', color=COLOR_NBR_LABEL,
                fontweight='bold', clip_on=True,
            )

    cap = capitals.get(country)
    if cap:
        cx, cy = cap['lon'], cap['lat']
        ax.plot(cx, cy, marker='o', markersize=CAP_MARKERSIZE, color=COLOR_CAP_DOT,
                markeredgecolor=COLOR_LABEL, markeredgewidth=CAP_EDGE_WIDTH, zorder=5)
        ax.text(cx + (maxx - minx) * 0.015 + CAP_LABEL_OFFSET, cy, cap['city'],
                fontsize=CAPITAL_FONTSIZE, va='center', color='white', fontweight='bold',
                clip_on=True, zorder=5)

    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.set_axis_off()

    plt.tight_layout(pad=0.4)
    safe_name = country.replace('/', '_').replace(' ', '_')
    fig.savefig(f'{OUTPUT_DIR}/{safe_name}.svg', format='svg', bbox_inches='tight')
    plt.close(fig)

print(f'\nDone – {total} SVGs saved to ./{OUTPUT_DIR}/')
