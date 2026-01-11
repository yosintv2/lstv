import json, os, re, glob
from datetime import datetime, timedelta

DOMAIN = "https://tv.cricfoot.net"
NOW = datetime.now()
TODAY_DATE = NOW.date()

# 1. DATE LOGIC (Friday to Thursday)
days_since_friday = (TODAY_DATE.weekday() - 4) % 7
START_WEEK = TODAY_DATE - timedelta(days=days_since_friday)

TOP_LEAGUE_IDS = [7, 35, 23, 17]

def slugify(t): 
    return re.sub(r'[^a-z0-9]+', '-', str(t).lower()).strip('-')

# 2. LOAD TEMPLATES
templates = {}
for name in ['home', 'match', 'channel']:
    with open(f'{name}_template.html', 'r', encoding='utf-8') as f:
        templates[name] = f.read()

# 3. LOAD LOCAL DATA FROM date/*.json
all_matches = []
seen_match_ids = set()

# Scanning local folder instead of API
for f in glob.glob("date/*.json"):
    with open(f, 'r', encoding='utf-8') as j:
        try:
            data = json.load(j)
            for m in data:
                mid = m.get('match_id')
                if mid and mid not in seen_match_ids:
                    all_matches.append(m)
                    seen_match_ids.add(mid)
        except Exception as e:
            print(f"Error reading {f}: {e}")

channels_data = {}
sitemap_urls = [DOMAIN + "/"]

# 4. GENERATE PAGES
for i in range(7):
    day = START_WEEK + timedelta(days=i)
    fname = "index.html" if day == TODAY_DATE else f"{day.strftime('%Y-%m-%d')}.html"
    
    if fname != "index.html":
        sitemap_urls.append(f"{DOMAIN}/{fname}")

    # GENERATE MENU SPECIFIC TO THIS DAY (to show "clicked" effect)
    current_page_menu = ""
    for j in range(7):
        m_day = START_WEEK + timedelta(days=j)
        m_fname = "index.html" if m_day == TODAY_DATE else f"{m_day.strftime('%Y-%m-%d')}.html"
        active_class = "active" if m_day == day else ""
        current_page_menu += f'<a href="{DOMAIN}/{m_fname}" class="date-btn {active_class}"><div>{m_day.strftime("%a")}</div><b>{m_day.strftime("%b %d")}</b></a>'

    # Filter matches for the specific day
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
        sitemap_urls.append(m_url)
        
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
            pills = ""
            for ch in c['channels']:
                ch_slug = slugify(ch)
                ch_url = f"{DOMAIN}/channel/{ch_slug}/"
                pills += f'<a href="{ch_url}" class="mx-1 text-blue-600 underline text-xs">{ch}</a>'
                
                if ch not in channels_data:
                    channels_data[ch] = []
                    sitemap_urls.append(ch_url)
                if m not in channels_data[ch]:
                    channels_data[ch].append(m)

            rows += f'<div class="flex justify-between p-4 border-b"><b>{c["country"]}</b><div>{pills}</div></div>'

        with open(f"{m_path}/index.html", "w", encoding='utf-8') as mf:
            mf.write(templates['match'].replace("{{FIXTURE}}", m['fixture'])
                     .replace("{{TIME}}", str(m['kickoff']))
                     .replace("{{VENUE}}", m.get('venue', 'TBA')).replace("{{BROADCAST_ROWS}}", rows)
                     .replace("{{LEAGUE}}", league).replace("{{DOMAIN}}", DOMAIN).replace("{{DATE}}", day.strftime('%d %b %Y')))

    # Write the Final Page
    with open(fname, "w", encoding='utf-8') as df:
        output = templates['home'].replace("{{MATCH_LISTING}}", listing_html)
        output = output.replace("{{WEEKLY_MENU}}", current_page_menu)
        output = output.replace("{{DOMAIN}}", DOMAIN)
        output = output.replace("{{DISPLAY_DATE}}", day.strftime("%A, %B %d, %Y")) # Shown below search bar
        output = output.replace("{{PAGE_TITLE}}", f"Soccer TV Schedule {day.strftime('%Y-%m-%d')}")
        df.write(output)

# Generate Channel Pages
for ch_name, ms in channels_data.items():
    c_slug = slugify(ch_name)
    c_dir = f"channel/{c_slug}"
    os.makedirs(c_dir, exist_ok=True)
    c_listing = "".join([f'<a href="{DOMAIN}/match/{slugify(x["fixture"])}/{datetime.fromtimestamp(x["kickoff"]).strftime("%Y%m%d")}/" class="match-row flex items-center p-4 bg-white"><div class="time-box"><span class="local-time" data-unix="{x["kickoff"]}">{datetime.fromtimestamp(x["kickoff"]).strftime("%H:%M")}</span></div><div class="px-4"><span class="text-sm font-semibold">{x["fixture"]}</span></div></a>' for x in ms])
    with open(f"{c_dir}/index.html", "w", encoding='utf-8') as cf:
        cf.write(templates['channel'].replace("{{CHANNEL_NAME}}", ch_name).replace("{{MATCH_LISTING}}", c_listing).replace("{{DOMAIN}}", DOMAIN))

# Generate Sitemap
sitemap_content = '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
for url in sitemap_urls:
    sitemap_content += f'<url><loc>{url}</loc><lastmod>{NOW.strftime("%Y-%m-%d")}</lastmod></url>'
sitemap_content += '</urlset>'
with open("sitemap.xml", "w", encoding='utf-8') as sm:
    sm.write(sitemap_content)

print(f"Build Complete. Found {len(all_matches)} matches across {len(channels_data)} channels.")
