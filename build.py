import json, os, re, glob 
from datetime import datetime, timedelta, timezone

# --- CONFIGURATION ---
DOMAIN = "https://tv.cricfoot.net"
LOCAL_OFFSET = timezone(timedelta(hours=5)) 

NOW = datetime.now(LOCAL_OFFSET)
TODAY_DATE = NOW.date() 

MENU_START_DATE = TODAY_DATE - timedelta(days=3)
TOP_LEAGUE_IDS = [17, 35, 23, 7, 8, 34, 679]

ADS_CODE = '''
<div class="ad-container" style="margin: 20px 0; text-align: center;">
    <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-5525538810839147" crossorigin="anonymous"></script>
    <ins class="adsbygoogle" style="display:block" data-ad-client="ca-pub-5525538810839147" data-ad-slot="4345862479" data-ad-format="auto" data-full-width-responsive="true"></ins>
    <script>(adsbygoogle = window.adsbygoogle || []).push({});</script>
</div>
'''

def slugify(t): 
    return re.sub(r'[^a-z0-9]+', '-', str(t).lower()).strip('-')

# --- 1. LOAD TEMPLATES ---
templates = {}
for name in ['home', 'match', 'channel']:
    try:
        with open(f'{name}_template.html', 'r', encoding='utf-8') as f:
            templates[name] = f.read()
    except FileNotFoundError:
        print(f"CRITICAL ERROR: {name}_template.html not found.")

# --- 2. LOAD DATA ---
all_matches = []
seen_match_ids = set()
for f in glob.glob("date/*.json"):
    with open(f, 'r', encoding='utf-8') as j:
        try:
            data = json.load(j)
            for m in data:
                mid = m.get('match_id')
                if mid and mid not in seen_match_ids:
                    all_matches.append(m)
                    seen_match_ids.add(mid)
        except: continue

channels_data = {}
sitemap_urls = [DOMAIN + "/"]

# --- 3. PROCESS MATCHES ---
for m in all_matches:
    m_dt_local = datetime.fromtimestamp(int(m['kickoff']), tz=timezone.utc).astimezone(LOCAL_OFFSET)
    m_slug = slugify(m['fixture'])
    m_date_folder = m_dt_local.strftime('%Y%m%d')
    m_url = f"{DOMAIN}/match/{m_slug}/{m_date_folder}/"
    sitemap_urls.append(m_url)
    
    league = m.get('league', 'Other Football')
    
    # Channel data for channel pages
    for c in m.get('tv_channels', []):
        for ch in c['channels']:
            if ch not in channels_data: channels_data[ch] = []
            if int(m['kickoff']) > (NOW.timestamp() - 86400):
                if not any(x['m']['match_id'] == m['match_id'] for x in channels_data[ch]):
                    channels_data[ch].append({'m': m, 'dt': m_dt_local, 'league': league})

    # --- GENERATE MATCH PAGE ---
    m_path = f"match/{m_slug}/{m_date_folder}"
    os.makedirs(m_path, exist_ok=True)
    venue_val = m.get('venue') or m.get('stadium') or "To Be Announced"
    
    rows = ""
    for c in m.get('tv_channels', []):
        pills = "".join([f'<a href="{DOMAIN}/channel/{slugify(ch)}/" class="channel-pill">{ch}</a>' for ch in c['channels']])
        rows += f'''
        <div class="broadcast-row">
            <div class="country-name">{c["country"]}</div>
            <div class="channel-list">{pills}</div>
        </div>'''

    with open(f"{m_path}/index.html", "w", encoding='utf-8') as mf:
        m_html = templates['match'].replace("{{FIXTURE}}", m['fixture']).replace("{{DOMAIN}}", DOMAIN)
        m_html = m_html.replace("{{BROADCAST_ROWS}}", rows).replace("{{LEAGUE}}", league)
        m_html = m_html.replace("{{LOCAL_DATE}}", m_dt_local.strftime("%d %b %Y"))
        m_html = m_html.replace("{{LOCAL_TIME}}", m_dt_local.strftime("%H:%M"))
        m_html = m_html.replace("{{UNIX}}", str(m['kickoff'])).replace("{{VENUE}}", venue_val)
        m_html = m_html.replace("{{MATCH_ID}}", str(m.get('match_id', '')))
        mf.write(m_html)

# (Logic for Home and Channel pages remains the same as your original)
print("Static Files Generated Successfully.")
