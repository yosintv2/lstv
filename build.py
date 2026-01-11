import json, os, re, glob
from datetime import datetime, timedelta

# --- CONFIGURATION ---
DOMAIN = "https://tv.cricfoot.net"
NOW = datetime.now()
TODAY_DATE = NOW.date()

# Friday to Thursday Logic
days_since_friday = (TODAY_DATE.weekday() - 4) % 7
START_WEEK = TODAY_DATE - timedelta(days=days_since_friday)

TOP_LEAGUE_IDS = [7, 35, 23, 17]

# REPLACE WITH YOUR ACTUAL GOOGLE AD CODE
AD_CODE = '''
<div class="ad-container" style="padding: 20px; text-align: center; background: #f8fafc; border-bottom: 1px solid #e2e8f0;">
    <ins class="adsbygoogle"
         style="display:block"
         data-ad-format="fluid"
         data-ad-layout-key="-fb+5w+4e-db+86"
         data-ad-client="ca-pub-5525538810839147"
         data-ad-slot="YOUR_AD_SLOT_ID"></ins>
    <script>(adsbygoogle = window.adsbygoogle || []).push({});</script>
</div>
'''

def slugify(t): 
    return re.sub(r'[^a-z0-9]+', '-', str(t).lower()).strip('-')

# --- 1. LOAD TEMPLATES ---
templates = {}
for name in ['home', 'match', 'channel']:
    with open(f'{name}_template.html', 'r', encoding='utf-8') as f:
        templates[name] = f.read()

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
    
    # Build Menu
    current_page_menu = ""
    for j in range(7):
        m_day = START_WEEK + timedelta(days=j)
        m_fname = "index.html" if m_day == TODAY_DATE else f"{m_day.strftime('%Y-%m-%d')}.html"
        active_class = "active" if m_day == day else ""
        current_page_menu += f'<a href="{DOMAIN}/{m_fname}" class="date-btn {active_class}"><div>{m_day.strftime("%a")}</div><b>{m_day.strftime("%b %d")}</b></a>'

    # Filter and Sort
    day_matches = [m for m in all_matches if datetime.fromtimestamp(m['kickoff']).date() == day]
    day_matches.sort(key=lambda x: (x.get('league_id') not in TOP_LEAGUE_IDS, x.get('league', '')))

    listing_html, last_league = "", ""
    for m in day_matches:
        league = m.get('league', 'Other Football')
        
        # LOGIC: If league changes, insert Ad before the NEW header
        if league != last_league:
            if last_league != "":
                listing_html += AD_CODE # INSERT AD HERE
            listing_html += f'<div class="league-header">{league}</div>'
            last_league = league
        
        m_slug, m_date = slugify(m['fixture']), datetime.fromtimestamp(m['kickoff']).strftime('%Y%m%d')
        m_url = f"{DOMAIN}/match/{m_slug}/{m_date}/"
        
        listing_html += f'''
        <a href="{m_url}" class="match-row flex items-center p-4 bg-white group">
            <div class="time-box">
                <span class="font-bold text-blue-600 text-sm local-time" data-unix="{m['kickoff']}">{datetime.fromtimestamp(m['kickoff']).strftime('%H:%M')}</span>
            </div>
            <div class="flex-1 px-4">
                <span class="text-slate-800 font-semibold text-sm md:text-base">{m['fixture']}</span>
            </div>
        </a>'''

    # Final Page Write
    with open(fname, "w", encoding='utf-8') as df:
        output = templates['home'].replace("{{MATCH_LISTING}}", listing_html)
        output = output.replace("{{WEEKLY_MENU}}", current_page_menu)
        output = output.replace("{{DOMAIN}}", DOMAIN)
        output = output.replace("{{SELECTED_DATE}}", day.strftime("%A, %b %d, %Y"))
        output = output.replace("{{PAGE_TITLE}}", f"Soccer TV Schedule {day.strftime('%Y-%m-%d')}")
        df.write(output)

# ... (Channel and Sitemap generation remains same) ...
print("Build Complete.")
