import json, os, re, glob
from datetime import datetime, timedelta, timezone

# --- CONFIGURATION ---
DOMAIN = "https://tv.cricfoot.net"

# 1. SET YOUR TARGET OFFSET (e.g., GMT+5)
# This ensures early morning matches (02:00, 04:00) group with the NEXT day correctly.
TARGET_OFFSET = timezone(timedelta(hours=5)) 

# Force the "current" time to align with your target timezone
NOW = datetime.now(TARGET_OFFSET)
TODAY_DATE = NOW.date()

# Friday to Thursday Logic
days_since_friday = (TODAY_DATE.weekday() - 4) % 7
START_WEEK = TODAY_DATE - timedelta(days=days_since_friday)

TOP_LEAGUE_IDS = [7, 35, 23, 17]

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

# --- 3. GENERATE DAILY PAGES ---
for i in range(7):
    day = START_WEEK + timedelta(days=i)
    fname = "index.html" if day == TODAY_DATE else f"{day.strftime('%Y-%m-%d')}.html"
    
    if fname != "index.html":
        sitemap_urls.append(f"{DOMAIN}/{fname}")

    # Build Dynamic Menu
    current_page_menu = ""
    for j in range(7):
        m_day = START_WEEK + timedelta(days=j)
        m_fname = "/" if m_day == TODAY_DATE else f"{m_day.strftime('%Y-%m-%d')}.html"
        active_class = "active" if m_day == day else ""
        current_page_menu += f'<a href="{DOMAIN}/{m_fname}" class="date-btn {active_class}"><div>{m_day.strftime("%a")}</div><b>{m_day.strftime("%b %d")}</b></a>'

    # FIX: Filter matches by converting UTC timestamp to the LOCAL target date
    day_matches = []
    for m in all_matches:
        # Convert Unix to UTC first, then adjust to the target offset
        m_dt_local = datetime.fromtimestamp(int(m['kickoff']), tz=timezone.utc).astimezone(TARGET_OFFSET)
        if m_dt_local.date() == day:
            day_matches.append(m)

    day_matches.sort(key=lambda x: (x.get('league_id') not in TOP_LEAGUE_IDS, x.get('league', ''), x['kickoff']))

    listing_html, last_league = "", ""
    for m in day_matches:
        league = m.get('league', 'Other Football')
        if league != last_league:
            listing_html += f'<div class="league-header">{league}</div>'
            last_league = league
        
        m_dt_local = datetime.fromtimestamp(int(m['kickoff']), tz=timezone.utc).astimezone(TARGET_OFFSET)
        m_slug = slugify(m['fixture'])
        m_date_folder = m_dt_local.strftime('%Y%m%d')
        m_url = f"{DOMAIN}/match/{m_slug}/{m_date_folder}/"
        sitemap_urls.append(m_url)
        
        # Displaying Date and Time based on target local timezone
        listing_html += f'''
        <a href="{m_url}" class="match-row flex items-center p-4 bg-white group">
            <div class="time-box" style="min-width: 95px; text-align: center; border-right: 1px solid #edf2f7; margin-right: 10px;">
                <div class="text-[10px] uppercase text-slate-400 font-bold">{m_dt_local.strftime('%d %b')}</div>
                <div class="font-bold text-blue-600 text-sm">{m_dt_local.strftime('%H:%M')}</div>
            </div>
            <div class="flex-1">
                <span class="text-slate-800 font-semibold text-sm md:text-base">{m['fixture']}</span>
            </div>
        </a>'''

        # --- 4. GENERATE MATCH PAGES ---
        m_path = f"match/{m_slug}/{m_date_folder}"
        os.makedirs(m_path, exist_ok=True)
        
        rows = ""
        for c in m.get('tv_channels', []):
            pills = "".join([f'<a href="{DOMAIN}/channel/{slugify(ch)}/" class="mx-1 text-blue-600 underline text-xs">{ch}</a>' for ch in c['channels']])
            for ch in c['channels']:
                if ch not in channels_data: channels_data[ch] = []
                if m not in channels_data[ch]: channels_data[ch].append(m)
            rows += f'<div class="flex justify-between p-4 border-b"><b>{c["country"]}</b><div>{pills}</div></div>'

        with open(f"{m_path}/index.html", "w", encoding='utf-8') as mf:
            m_html = templates['match'].replace("{{FIXTURE}}", m['fixture'])
            m_html = m_html.replace("{{DOMAIN}}", DOMAIN)
            m_html = m_html.replace("{{BROADCAST_ROWS}}", rows)
            m_html = m_html.replace("{{LEAGUE}}", league)
            m_html = m_html.replace("{{DATE}}", m_dt_local.strftime('%d %b %Y'))
            m_html = m_html.replace("{{TIME}}", m_dt_local.strftime('%H:%M'))
            mf.write(m_html)

    # WRITE DAILY FILE
    with open(fname, "w", encoding='utf-8') as df:
        output = templates['home'].replace("{{MATCH_LISTING}}", listing_html)
        output = output.replace("{{WEEKLY_MENU}}", current_page_menu)
        output = output.replace("{{DOMAIN}}", DOMAIN)
        output = output.replace("{{SELECTED_DATE}}", day.strftime("%A, %b %d, %Y"))
        output = output.replace("{{PAGE_TITLE}}", f"Soccer TV Channels For {day.strftime('%A, %b %d, %Y')} - CricFootTV")
        df.write(output)

# --- 5. CHANNEL PAGES ---
for ch_name, ms in channels_data.items():
    c_slug = slugify(ch_name)
    c_dir = f"channel/{c_slug}"
    os.makedirs(c_dir, exist_ok=True)
    c_listing = "".join([f'<div class="match-row p-4">{x["fixture"]}</div>' for x in ms]) # Simplified for brevity
    with open(f"{c_dir}/index.html", "w", encoding='utf-8') as cf:
        cf.write(templates['channel'].replace("{{CHANNEL_NAME}}", ch_name).replace("{{MATCH_LISTING}}", c_listing).replace("{{DOMAIN}}", DOMAIN))

print(f"Build Successful. Matches grouped by {TARGET_OFFSET} local time.")
