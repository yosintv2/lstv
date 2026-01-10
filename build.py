import json, os, re, glob
from datetime import datetime, timedelta

DOMAIN = "https://tv.cricfoot.net"
# Set reference time
NOW = datetime.now()
TODAY_DATE = NOW.date()

TOP_LEAGUE_IDS = [23, 17]

# Friday to Thursday Logic
days_since_friday = (TODAY_DATE.weekday() - 4) % 7
START_WEEK = TODAY_DATE - timedelta(days=days_since_friday)

def slugify(t): return re.sub(r'[^a-z0-9]+', '-', t.lower()).strip('-')

templates = {}
for name in ['home', 'match', 'channel']:
    with open(f'{name}_template.html', 'r', encoding='utf-8') as f:
        templates[name] = f.read()

# Load Data and REMOVE DUPLICATES
all_matches = []
seen_match_ids = set()

for f in glob.glob("date/*.json"):
    with open(f, 'r', encoding='utf-8') as j:
        try:
            data = json.load(j)
            for m in data:
                mid = m.get('match_id')
                if mid not in seen_match_ids:
                    all_matches.append(m)
                    seen_match_ids.add(mid)
        except: continue

channels_data = {}
sitemap_urls = [DOMAIN + "/"]

# Generate Weekly Menu
menu_html = ""
for i in range(7):
    day = START_WEEK + timedelta(days=i)
    fname = "index.html" if day == TODAY_DATE else f"{day.strftime('%Y-%m-%d')}.html"
    active_class = "active" if day == TODAY_DATE else ""
    menu_html += f'<a href="{DOMAIN}/{fname}" class="date-btn {active_class}"><div>{day.strftime("%a")}</div><b>{day.strftime("%b %d")}</b></a>'

# Generate Daily Pages
for i in range(7):
    day = START_WEEK + timedelta(days=i)
    fname = "index.html" if day == TODAY_DATE else f"{day.strftime('%Y-%m-%d')}.html"
    sitemap_urls.append(f"{DOMAIN}/{fname}")
    
    # Accurate Date Filtering
    day_matches = [m for m in all_matches if datetime.fromtimestamp(m['kickoff']).date() == day]
    day_matches.sort(key=lambda x: (x.get('league_id') not in TOP_LEAGUE_IDS, x.get('match_id', 99999999), x['kickoff']))

    listing_html, last_league = "", ""
    for m in day_matches:
        league = m.get('league', 'Other')
        if league != last_league:
            listing_html += f'<div class="league-header">{league}</div>'
            last_league = league
        
        m_slug, m_date = slugify(m['fixture']), datetime.fromtimestamp(m['kickoff']).strftime('%Y%m%d')
        m_url = f"{DOMAIN}/match/{m_slug}/{m_date}/"
        
        # Pre-calculated time for instant display (UTC)
        display_time = datetime.fromtimestamp(m['kickoff']).strftime('%H:%M')
        
        listing_html += f'''
        <a href="{m_url}" class="match-row flex items-center p-4 bg-white group">
            <div class="time-box">
                <span class="font-bold text-blue-600 text-sm local-time" data-unix="{m['kickoff']}">{display_time}</span>
            </div>
            <div class="flex-1 px-4">
                <span class="text-slate-800 font-semibold text-sm md:text-base">{m['fixture']}</span>
            </div>
        </a>'''
        
        # Match Page Generation
        m_path = f"match/{m_slug}/{m_date}"
        os.makedirs(m_path, exist_ok=True)
        rows = ""
        for c in m.get('tv_channels', []):
            pills = "".join([f'<a href="{DOMAIN}/channel/{slugify(ch)}/" class="mx-1 text-blue-600 underline text-xs">{ch}</a>' for ch in c['channels']])
            rows += f'<div class="flex justify-between p-4 border-b"><b>{c["country"]}</b><div>{pills}</div></div>'
            for ch in c['channels']: channels_data.setdefault(ch, []).append(m)

        with open(f"{m_path}/index.html", "w", encoding='utf-8') as mf:
            mf.write(templates['match'].replace("{{FIXTURE}}", m['fixture'])
                     .replace("{{TIME}}", str(m['kickoff']))
                     .replace("{{VENUE}}", m.get('venue', 'TBA')).replace("{{BROADCAST_ROWS}}", rows)
                     .replace("{{LEAGUE}}", league).replace("{{DOMAIN}}", DOMAIN).replace("{{DATE}}", day.strftime('%d %b %Y')))

    with open(fname, "w", encoding='utf-8') as df:
        df.write(templates['home'].replace("{{MATCH_LISTING}}", listing_html).replace("{{WEEKLY_MENU}}", menu_html).replace("{{DOMAIN}}", DOMAIN).replace("{{PAGE_TITLE}}", f"Soccer TV Schedule {day.strftime('%Y-%m-%d')}"))

print("Build Complete.")
