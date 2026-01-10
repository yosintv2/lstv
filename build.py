import json, os, re, glob
from datetime import datetime, timedelta

DOMAIN = "https://tv.cricfoot.net"
NOW = datetime.now()
TODAY_DATE = NOW.date()

# Friday to Thursday Logic
# 4 is Friday. Calculate how many days to subtract to reach the most recent Friday.
days_since_friday = (TODAY_DATE.weekday() - 4) % 7
START_WEEK = TODAY_DATE - timedelta(days=days_since_friday)

def slugify(t): return re.sub(r'[^a-z0-9]+', '-', t.lower()).strip('-')

# Load Templates
templates = {}
for name in ['home', 'match', 'channel']:
    with open(f'{name}_template.html', 'r', encoding='utf-8') as f:
        templates[name] = f.read()

# Load Data
all_matches = []
for f in glob.glob("date/*.json"):
    with open(f, 'r', encoding='utf-8') as j:
        all_matches.extend(json.load(j))

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
    
    day_matches = [m for m in all_matches if datetime.fromtimestamp(m['kickoff']).date() == day]
    day_matches.sort(key=lambda x: (x.get('league') != "Premier League", x['kickoff']))

    listing_html, last_league = "", ""
    for m in day_matches:
        league = m.get('league', 'Other')
        if league != last_league:
            listing_html += f'<div class="league-header" style="background:#334155;color:#fff;padding:8px;">{league}</div>'
            last_league = league
        
        m_slug, m_date = slugify(m['fixture']), datetime.fromtimestamp(m['kickoff']).strftime('%Y%m%d')
        m_url = f"{DOMAIN}/match/{m_slug}/{m_date}/"
        listing_html += f'<a href="{m_url}" class="match-row flex items-center p-3 border-b bg-white"><span class="w-16 font-bold text-blue-600">{datetime.fromtimestamp(m["kickoff"]).strftime("%H:%M")}</span><span>{m["fixture"]}</span></a>'
        
        # Build Match Page
        m_path = f"match/{m_slug}/{m_date}"
        os.makedirs(m_path, exist_ok=True)
        rows = ""
        for c in m.get('tv_channels', []):
            pills = "".join([f'<a href="{DOMAIN}/channel/{slugify(ch)}/" class="mx-1 text-blue-600 underline text-xs">{ch}</a>' for ch in c['channels']])
            rows += f'<div class="flex justify-between p-4 border-b"><b>{c["country"]}</b><div>{pills}</div></div>'
            for ch in c['channels']: channels_data.setdefault(ch, []).append(m)

        with open(f"{m_path}/index.html", "w") as mf:
            mf.write(templates['match'].replace("{{FIXTURE}}", m['fixture']).replace("{{TIME}}", datetime.fromtimestamp(m['kickoff']).strftime('%H:%M'))
                     .replace("{{VENUE}}", m.get('venue', 'TBA')).replace("{{BROADCAST_ROWS}}", rows)
                     .replace("{{LEAGUE}}", league).replace("{{DOMAIN}}", DOMAIN).replace("{{DATE}}", day.strftime('%d %b %Y')))

    with open(fname, "w") as df:
        df.write(templates['home'].replace("{{MATCH_LISTING}}", listing_html).replace("{{WEEKLY_MENU}}", menu_html).replace("{{DOMAIN}}", DOMAIN).replace("{{PAGE_TITLE}}", f"Soccer TV Schedule {day.strftime('%Y-%m-%d')}"))

# Build Channel Pages
for ch, ms in channels_data.items():
    c_slug = slugify(ch)
    os.makedirs(f"channel/{c_slug}", exist_ok=True)
    s_url = f"{DOMAIN}/channel/{c_slug}/"
    sitemap_urls.append(s_url)
    c_listing = "".join([f'<div class="p-4 border-b">{x["fixture"]} - {datetime.fromtimestamp(x["kickoff"]).strftime("%H:%M")}</div>' for x in ms])
    with open(f"channel/{c_slug}/index.html", "w") as cf:
        cf.write(templates['channel'].replace("{{CHANNEL_NAME}}", ch).replace("{{MATCH_LISTING}}", c_listing).replace("{{DOMAIN}}", DOMAIN))

# Automatic Sitemap Generation
with open("sitemap.xml", "w") as sm:
    xml = '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    for u in sitemap_urls: xml += f'<url><loc>{u}</loc><lastmod>{datetime.now().strftime("%Y-%m-%d")}</lastmod></url>'
    sm.write(xml + '</urlset>')

print("Build Complete: 7 days (Fri-Thu), sitemap.xml, and LiveSoccerTV CSS integrated.")
