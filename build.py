import json, os, re, glob
from datetime import datetime, timedelta, timezone

# --- CONFIGURATION ---
DOMAIN = "https://tv.cricfoot.net"
LOCAL_OFFSET = timezone(timedelta(hours=5)) 

NOW = datetime.now(LOCAL_OFFSET)
TODAY_DATE = NOW.date()

# CENTER LOGIC: To make Today the 4th item, we start the menu 3 days ago
MENU_START_DATE = TODAY_DATE - timedelta(days=3)

TOP_LEAGUE_IDS = [7, 35, 23, 17]

# Google Ads Code Block (Wrapped in a class for JS control)
ADS_CODE = '''
<div class="ad-container google-ad-slot" style="margin: 20px 0; text-align: center;">
    <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-5525538810839147" crossorigin="anonymous"></script>
    <ins class="adsbygoogle"
         style="display:block"
         data-ad-client="ca-pub-5525538810839147"
         data-ad-slot="4345862479"
         data-ad-format="auto"
         data-full-width-responsive="true"></ins>
    <script>(adsbygoogle = window.adsbygoogle || []).push({});</script>
</div>
'''

# Enhanced CSS: Responsive, Orange Hover, and طراحی consistency
MENU_CSS = '''
<style>
    .weekly-menu-container {
        display: flex;
        width: 100%;
        gap: 4px;
        padding: 10px 5px;
        box-sizing: border-box;
        justify-content: space-between;
    }
    .date-btn {
        flex: 1;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 8px 2px;
        text-decoration: none;
        border-radius: 6px;
        background: #fff;
        border: 1px solid #e2e8f0;
        min-width: 0; 
        transition: all 0.2s ease;
    }
    .date-btn div { font-size: 9px; text-transform: uppercase; color: #64748b; font-weight: bold; }
    .date-btn b { font-size: 10px; color: #1e293b; white-space: nowrap; }
    
    /* Orange Hover Effect */
    .date-btn:hover { border-color: #ff9800; background-color: #fffaf0; }
    .date-btn:hover b { color: #ff9800; }
    
    .date-btn.active { background: #2563eb; border-color: #2563eb; }
    .date-btn.active div, .date-btn.active b { color: #fff; }
    .date-btn.active:hover { background: #1d4ed8; }

    /* Search Logic: Hide ads when searching */
    body.is-searching .google-ad-slot { display: none !important; }

    @media (max-width: 480px) {
        .date-btn b { font-size: 8px; }
        .date-btn div { font-size: 7px; }
        .weekly-menu-container { gap: 2px; padding: 5px 2px; }
    }
</style>
'''

# This JS should be in your home_template.html or channel_template.html
SEARCH_JS = '''
<script>
document.getElementById('searchInput')?.addEventListener('input', function(e) {
    if(e.target.value.trim().length > 0) {
        document.body.classList.add('is-searching');
    } else {
        document.body.classList.remove('is-searching');
    }
});
</script>
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

# --- 3. GENERATE DAILY PAGES ---
for i in range(7):
    day = MENU_START_DATE + timedelta(days=i)
    fname = "index.html" if day == TODAY_DATE else f"{day.strftime('%Y-%m-%d')}.html"
    if fname != "index.html": sitemap_urls.append(f"{DOMAIN}/{fname}")

    # Build Menu
    page_specific_menu = f'{MENU_CSS}<div class="weekly-menu-container">'
    for j in range(7):
        m_day = MENU_START_DATE + timedelta(days=j)
        m_fname = "index.html" if m_day == TODAY_DATE else f"{m_day.strftime('%Y-%m-%d')}.html"
        active_class = "active" if m_day == day else ""
        page_specific_menu += f'''
        <a href="{DOMAIN}/{m_fname}" class="date-btn {active_class}">
            <div>{m_day.strftime("%a")}</div>
            <b>{m_day.strftime("%b %d")}</b>
        </a>'''
    page_specific_menu += '</div>'

    day_matches = []
    for m in all_matches:
        m_dt_local = datetime.fromtimestamp(int(m['kickoff']), tz=timezone.utc).astimezone(LOCAL_OFFSET)
        if m_dt_local.date() == day:
            day_matches.append(m)

    day_matches.sort(key=lambda x: (x.get('league_id') not in TOP_LEAGUE_IDS, x.get('league', 'Other Football'), x['kickoff']))

    listing_html, last_league = "", ""
    league_counter = 0

    for m in day_matches:
        league = m.get('league', 'Other Football')
        if league != last_league:
            if last_league != "":
                league_counter += 1
                if league_counter % 3 == 0: listing_html += ADS_CODE
            listing_html += f'<div class="league-header">{league}</div>'
            last_league = league
        
        m_dt_local = datetime.fromtimestamp(int(m['kickoff']), tz=timezone.utc).astimezone(LOCAL_OFFSET)
        m_url = f"{DOMAIN}/match/{slugify(m['fixture'])}/{m_dt_local.strftime('%Y%m%d')}/"
        sitemap_urls.append(m_url)
        
        listing_html += f'''
        <a href="{m_url}" class="match-row flex items-center p-4 bg-white group">
            <div class="time-box" style="min-width: 95px; text-align: center; border-right: 1px solid #edf2f7; margin-right: 10px;">
                <div class="text-[10px] uppercase text-slate-400 font-bold auto-date" data-unix="{m['kickoff']}">{m_dt_local.strftime('%d %b')}</div>
                <div class="font-bold text-blue-600 text-sm auto-time" data-unix="{m['kickoff']}">{m_dt_local.strftime('%H:%M')}</div>
            </div>
            <div class="flex-1">
                <span class="text-slate-800 font-semibold text-sm md:text-base">{m['fixture']}</span>
            </div>
        </a>'''

        # Channel Data Aggregation (Filtering for Upcoming only)
        if int(m['kickoff']) > (datetime.now(timezone.utc).timestamp() - 7200): # Show matches starting from 2 hours ago onwards
            for c in m.get('tv_channels', []):
                for ch in c['channels']:
                    if ch not in channels_data: channels_data[ch] = []
                    if not any(x['m']['match_id'] == m['match_id'] for x in channels_data[ch]):
                        channels_data[ch].append({'m': m, 'dt': m_dt_local, 'league': league})

    if listing_html != "": listing_html += ADS_CODE

    with open(fname, "w", encoding='utf-8') as df:
        output = templates['home'].replace("{{MATCH_LISTING}}", listing_html).replace("{{WEEKLY_MENU}}", page_specific_menu + SEARCH_JS)
        output = output.replace("{{DOMAIN}}", DOMAIN).replace("{{SELECTED_DATE}}", day.strftime("%A, %b %d, %Y"))
        df.write(output)

# --- 5. CHANNEL PAGES (UPCOMING ONLY & NEW DESIGN) ---
for ch_name, matches in channels_data.items():
    c_slug = slugify(ch_name)
    c_dir = f"channel/{c_slug}"
    os.makedirs(c_dir, exist_ok=True)
    
    # Mirror the index.html design menu
    channel_menu = f'{MENU_CSS}<div class="weekly-menu-container">'
    for j in range(7):
        m_day = MENU_START_DATE + timedelta(days=j)
        m_fname = "index.html" if m_day == TODAY_DATE else f"{m_day.strftime('%Y-%m-%d')}.html"
        channel_menu += f'<a href="{DOMAIN}/{m_fname}" class="date-btn"><div>{m_day.strftime("%a")}</div><b>{m_day.strftime("%b %d")}</b></a>'
    channel_menu += '</div>'

    # Filter matches to strictly upcoming (current time onwards)
    current_ts = datetime.now(timezone.utc).timestamp()
    upcoming_matches = [x for x in matches if int(x['m']['kickoff']) > current_ts]
    upcoming_matches.sort(key=lambda x: x['m']['kickoff'])

    c_listing = ""
    last_c_league = ""
    c_league_count = 0

    for item in upcoming_matches:
        m, dt, m_league = item['m'], item['dt'], item['league']
        
        # Consistent League Header Design
        if m_league != last_c_league:
            if last_c_league != "":
                c_league_count += 1
                if c_league_count % 3 == 0: c_listing += ADS_CODE
            c_listing += f'<div class="league-header">{m_league}</div>'
            last_c_league = m_league

        c_listing += f'''
        <a href="{DOMAIN}/match/{slugify(m['fixture'])}/{dt.strftime('%Y%m%d')}/" class="match-row flex items-center p-4 bg-white group">
            <div class="time-box" style="min-width: 95px; text-align: center; border-right: 1px solid #edf2f7; margin-right: 10px;">
                <div class="text-[10px] uppercase text-slate-400 font-bold auto-date" data-unix="{m['kickoff']}">{dt.strftime('%d %b')}</div>
                <div class="font-bold text-blue-600 text-sm auto-time" data-unix="{m['kickoff']}">{dt.strftime('%H:%M')}</div>
            </div>
            <div class="flex-1">
                <span class="text-slate-800 font-semibold text-sm md:text-base">{m['fixture']}</span>
            </div>
        </a>'''

    with open(f"{c_dir}/index.html", "w", encoding='utf-8') as cf:
        final_channel_html = templates['channel'].replace("{{CHANNEL_NAME}}", ch_name)
        final_channel_html = final_channel_html.replace("{{MATCH_LISTING}}", c_listing)
        final_channel_html = final_channel_html.replace("{{DOMAIN}}", DOMAIN)
        final_channel_html = final_channel_html.replace("{{WEEKLY_MENU}}", channel_menu + SEARCH_JS)
        cf.write(final_channel_html)

# --- 6. SITEMAP ---
sitemap_content = '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
for url in list(set(sitemap_urls)):
    sitemap_content += f'<url><loc>{url}</loc><lastmod>{NOW.strftime("%Y-%m-%d")}</lastmod></url>'
sitemap_content += '</urlset>'
with open("sitemap.xml", "w", encoding='utf-8') as sm: sm.write(sitemap_content)

print(f"Build Complete! Today is {TODAY_DATE}. Orange hover and search-ad-hide logic active.")
