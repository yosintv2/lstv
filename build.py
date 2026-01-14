import json, os, re, glob
from datetime import datetime, timedelta, timezone

# --- CONFIGURATION ---
DOMAIN = "https://tv.cricfoot.net"
LOCAL_OFFSET = timezone(timedelta(hours=5))

NOW = datetime.now(LOCAL_OFFSET)
TODAY_DATE = NOW.date()

# MENU: Today centered (7 days total)
MENU_START_DATE = TODAY_DATE - timedelta(days=3)

TOP_LEAGUE_IDS = [17, 35, 23, 7, 8, 34, 679]

# Ads (UNCHANGED)
ADS_CODE = '''
<div class="ad-container" style="margin: 20px 0; text-align: center;">
</div>
'''

# Menu CSS (UNCHANGED)
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
        transition: all 0.2s;
    }
    .date-btn div { font-size: 9px; text-transform: uppercase; color: #64748b; font-weight: bold; }
    .date-btn b { font-size: 10px; color: #1e293b; white-space: nowrap; }
    .date-btn.active { background: #2563eb; border-color: #2563eb; }
    .date-btn.active div, .date-btn.active b { color: #fff; }

    @media (max-width: 480px) {
        .date-btn b { font-size: 8px; }
        .date-btn div { font-size: 7px; }
        .weekly-menu-container { gap: 2px; padding: 5px 2px; }
    }
</style>
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
seen_ids = set()

for f in glob.glob("date/*.json"):
    with open(f, 'r', encoding='utf-8') as j:
        try:
            for m in json.load(j):
                mid = m.get('match_id')
                if mid and mid not in seen_ids:
                    all_matches.append(m)
                    seen_ids.add(mid)
        except:
            pass

channels_data = {}
sitemap_urls = [DOMAIN + "/"]

# --- 3. MATCH PAGES + CHANNEL DATA ---
for m in all_matches:
    dt = datetime.fromtimestamp(int(m['kickoff']), tz=timezone.utc).astimezone(LOCAL_OFFSET)
    slug = slugify(m['fixture'])
    folder = dt.strftime('%Y%m%d')
    url = f"{DOMAIN}/match/{slug}/{folder}/"
    sitemap_urls.append(url)

    league = m.get('league', 'Other Football')

    # Channel mapping
    for c in m.get('tv_channels', []):
        for ch in c['channels']:
            channels_data.setdefault(ch, [])
            if int(m['kickoff']) > NOW.timestamp() - 86400:
                if not any(x['m']['match_id'] == m['match_id'] for x in channels_data[ch]):
                    channels_data[ch].append({'m': m, 'dt': dt, 'league': league})

    # Match page
    path = f"match/{slug}/{folder}"
    os.makedirs(path, exist_ok=True)

    rows = ""
    count = 0
    for c in m.get('tv_channels', []):
        count += 1
        pills = "".join([
            f'<a href="{DOMAIN}/channel/{slugify(ch)}/" '
            f'style="display:inline-block;background:#f1f5f9;color:#2563eb;'
            f'padding:2px 8px;border-radius:4px;margin:2px;'
            f'text-decoration:none;font-weight:600;border:1px solid #e2e8f0;">{ch}</a>'
            for ch in c['channels']
        ])
        rows += f'''
        <div style="display:flex;padding:12px;border-bottom:1px solid #edf2f7;background:#fff;">
            <div style="width:100px;font-weight:800;color:#475569;font-size:13px;">{c["country"]}</div>
            <div style="flex:1;display:flex;flex-wrap:wrap;gap:4px;">{pills}</div>
        </div>'''
        if count % 10 == 0:
            rows += ADS_CODE

    html = templates['match']
    html = html.replace("{{FIXTURE}}", m['fixture']).replace("{{DOMAIN}}", DOMAIN)
    html = html.replace("{{BROADCAST_ROWS}}", rows)
    html = html.replace("{{LEAGUE}}", league)
    html = html.replace("{{LOCAL_DATE}}", f'<span class="auto-date" data-unix="{m["kickoff"]}">{dt.strftime("%d %b %Y")}</span>')
    html = html.replace("{{LOCAL_TIME}}", f'<span class="auto-time" data-unix="{m["kickoff"]}">{dt.strftime("%H:%M")}</span>')
    html = html.replace("{{UNIX}}", str(m['kickoff']))
    html = html.replace("{{VENUE}}", m.get('venue') or m.get('stadium') or "To Be Announced")

    with open(f"{path}/index.html", "w", encoding="utf-8") as f:
        f.write(html)

# --- 4. DAILY PAGES (ALL DATES, MENU SAME) ---
ALL_DATES = sorted({
    datetime.fromtimestamp(int(m['kickoff']), tz=timezone.utc)
    .astimezone(LOCAL_OFFSET).date()
    for m in all_matches
})

for day in ALL_DATES:
    fname = "index.html" if day == TODAY_DATE else f"{day}.html"
    if fname != "index.html":
        sitemap_urls.append(f"{DOMAIN}/{fname}")

    menu = f'{MENU_CSS}<div class="weekly-menu-container">'
    for i in range(7):
        d = MENU_START_DATE + timedelta(days=i)
        f2 = "index.html" if d == TODAY_DATE else f"{d}.html"
        menu += f'''
        <a href="{DOMAIN}/{f2}" class="date-btn {'active' if d == day else ''}">
            <div>{d.strftime("%a")}</div><b>{d.strftime("%b %d")}</b>
        </a>'''
    menu += '</div>'

    matches = [
        m for m in all_matches
        if datetime.fromtimestamp(int(m['kickoff']), tz=timezone.utc)
        .astimezone(LOCAL_OFFSET).date() == day
    ]

    matches.sort(key=lambda x: (
        x.get('league_id') not in TOP_LEAGUE_IDS,
        x.get('league', ''),
        x['kickoff']
    ))

    listing, last = "", ""
    counter = 0

    for m in matches:
        league = m.get('league', 'Other Football')
        if league != last:
            if last:
                counter += 1
                if counter % 3 == 0:
                    listing += ADS_CODE
            listing += f'<div class="league-header">{league}</div>'
            last = league

        dt = datetime.fromtimestamp(int(m['kickoff']), tz=timezone.utc).astimezone(LOCAL_OFFSET)
        listing += f'''
        <a href="{DOMAIN}/match/{slugify(m['fixture'])}/{dt.strftime('%Y%m%d')}/"
           class="match-row flex items-center p-4 bg-white border-b border-slate-100">
            <div class="time-box" style="min-width:95px;text-align:center;border-right:1px solid #edf2f7;margin-right:10px;">
                <div class="text-[10px] uppercase text-slate-400 font-bold auto-date" data-unix="{m['kickoff']}">{dt.strftime('%d %b')}</div>
                <div class="font-bold text-blue-600 text-sm auto-time" data-unix="{m['kickoff']}">{dt.strftime('%H:%M')}</div>
            </div>
            <div class="flex-1">
                <span class="text-slate-800 font-semibold">{m['fixture']}</span>
            </div>
        </a>'''

    if listing:
        listing += ADS_CODE

    page = templates['home']
    page = page.replace("{{MATCH_LISTING}}", listing)
    page = page.replace("{{WEEKLY_MENU}}", menu)
    page = page.replace("{{DOMAIN}}", DOMAIN)
    page = page.replace("{{SELECTED_DATE}}", day.strftime("%A, %b %d, %Y"))
    page = page.replace("{{PAGE_TITLE}}", f"TV Channels For {day.strftime('%A, %b %d, %Y')}")

    with open(fname, "w", encoding="utf-8") as f:
        f.write(page)

# --- 5. CHANNEL PAGES ---
for ch, items in channels_data.items():
    slug = slugify(ch)
    os.makedirs(f"channel/{slug}", exist_ok=True)
    sitemap_urls.append(f"{DOMAIN}/channel/{slug}/")

    listing = ""
    for i in sorted(items, key=lambda x: x['m']['kickoff']):
        m, dt, lg = i['m'], i['dt'], i['league']
        listing += f'''
        <a href="{DOMAIN}/match/{slugify(m['fixture'])}/{dt.strftime('%Y%m%d')}/"
           class="match-row flex items-center p-4 bg-white border-b border-slate-100">
            <div class="time-box" style="min-width:95px;text-align:center;border-right:1px solid #edf2f7;margin-right:10px;">
                <div class="text-[10px] uppercase text-slate-400 font-bold auto-date" data-unix="{m['kickoff']}">{dt.strftime('%d %b')}</div>
                <div class="font-bold text-blue-600 text-sm auto-time" data-unix="{m['kickoff']}">{dt.strftime('%H:%M')}</div>
            </div>
            <div class="flex-1">
                <span class="font-semibold">{m['fixture']}</span>
                <div class="text-[11px] text-blue-500 uppercase">{lg}</div>
            </div>
        </a>'''

    html = templates['channel']
    html = html.replace("{{CHANNEL_NAME}}", ch)
    html = html.replace("{{MATCH_LISTING}}", listing)
    html = html.replace("{{DOMAIN}}", DOMAIN)
    html = html.replace("{{WEEKLY_MENU}}", MENU_CSS)

    with open(f"channel/{slug}/index.html", "w", encoding="utf-8") as f:
        f.write(html)

# --- 6. SITEMAP ---
xml = '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
for u in sorted(set(sitemap_urls)):
    xml += f'<url><loc>{u}</loc><lastmod>{NOW.strftime("%Y-%m-%d")}</lastmod></url>'
xml += '</urlset>'

with open("sitemap.xml", "w", encoding="utf-8") as f:
    f.write(xml)

print("✅ Success: all dates generated, CSS & scripts untouched.")
