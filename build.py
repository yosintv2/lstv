import json, os, re, glob
from datetime import datetime, timedelta

# --- CONFIG ---
DOMAIN = "https://tv.cricfoot.net"
DATE_FOLDER = "date/*.json"

def slugify(t): return re.sub(r'[^a-z0-9]+', '-', t.lower()).strip('-')

# 1. DATA MERGING & DEDUPLICATION
all_matches = {}
for file_path in glob.glob(DATE_FOLDER):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for m in json.load(f):
                # Unique Key: Fixture + Kickoff timestamp to ignore duplicates
                uid = f"{m['fixture']}-{m['kickoff']}"
                if uid not in all_matches: all_matches[uid] = m
    except: pass

matches = sorted(all_matches.values(), key=lambda x: x['kickoff'])

# 2. SHARED ASSETS
today_dt = datetime.now()
date_menu = ""
for i in [-1, 0, 1]:
    d = today_dt + timedelta(days=i)
    lbl = ["Yesterday", "Today", "Tomorrow"][i+1]
    style = "bg-[#00a0e9] text-white" if i == 0 else "bg-slate-700 text-slate-300"
    date_menu += f'<a href="/" class="flex-1 text-center py-2 rounded text-[10px] font-black uppercase {style}">{lbl}<br>{d.strftime("%b %d")}</a>'

with open('home_template.html', 'r') as f: home_temp = f.read()
with open('match_template.html', 'r') as f: match_temp = f.read()
with open('channel_template.html', 'r') as f: chan_temp = f.read()

leagues_dict, channels_dict, sitemap_urls = {}, {}, [DOMAIN + "/"]

# 3. GENERATE MATCH PAGES
for m in matches:
    dt = datetime.fromtimestamp(m['kickoff'])
    t_str, d_str = dt.strftime('%H:%M'), dt.strftime('%d %b %Y')
    league, venue = m.get('league', 'Football'), m.get('venue', 'TBA')
    match_path = f"match/{slugify(m['fixture'])}/{dt.strftime('%Y%m%d')}"
    os.makedirs(match_path, exist_ok=True)

    rows, top_ch = "", []
    for c in m.get('tv_channels', []):
        pills = "".join([f'<a href="/channel/{slugify(ch)}/" class="pill">{ch}</a>' for ch in c['channels']])
        rows += f'<div class="row"><div class="c-name">{c["country"]}</div><div class="ch-list">{pills}</div></div>'
        top_ch.extend(c['channels'])

    m_page = match_temp.replace("{{FIXTURE}}", m['fixture']).replace("{{LEAGUE}}", league) \
                      .replace("{{TIME}}", t_str).replace("{{DATE}}", d_str) \
                      .replace("{{VENUE}}", venue).replace("{{BROADCAST_ROWS}}", rows) \
                      .replace("{{TOP_CHANNELS}}", ", ".join(list(set(top_ch))[:5]))
    
    with open(f"{match_path}/index.html", "w") as f: f.write(m_page)
    sitemap_urls.append(f"{DOMAIN}/{match_path}/")
    leagues_dict.setdefault(league, []).append({"time": t_str, "fixture": m['fixture'], "url": f"/{match_path}/"})
    for c in m.get('tv_channels', []): 
        for ch in c['channels']: channels_dict.setdefault(ch, []).append(m)

# 4. GENERATE CHANNEL PAGES
for ch_name, ch_mats in channels_dict.items():
    c_path = f"channel/{slugify(ch_name)}"
    os.makedirs(c_path, exist_ok=True)
    c_list = "".join([f'<a href="/match/{slugify(x["fixture"])}/{datetime.fromtimestamp(x["kickoff"]).strftime("%Y%m%d")}/" class="match-card"><div class="time-col">{datetime.fromtimestamp(x["kickoff"]).strftime("%H:%M")}</div><div class="font-bold">{x["fixture"]}</div></a>' for x in ch_mats])
    with open(f"{c_path}/index.html", "w") as f: f.write(chan_temp.replace("{{CHANNEL_NAME}}", ch_name).replace("{{MATCH_LISTING}}", c_list))
    sitemap_urls.append(f"{DOMAIN}/{c_path}/")

# 5. GENERATE HOME & SITEMAP
h_list = "".join([f'<div class="mb-6"><div class="league-title">{l}</div>' + "".join([f'<a href="{mx["url"]}" class="match-card"><div class="time-col">{mx["time"]}</div><div class="font-bold">{mx["fixture"]}</div></a>' for mx in ms]) + '</div>' for l, ms in leagues_dict.items()])
with open("index.html", "w") as f: f.write(home_temp.replace("{{MATCH_LISTING}}", h_list).replace("{{DATE_MENU}}", date_menu).replace("{{TODAY}}", today_dt.strftime("%A, %b %d")))

# XML SITEMAP GENERATION
sitemap_xml = '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
for url in sitemap_urls:
    sitemap_xml += f'<url><loc>{url}</loc><lastmod>{today_dt.strftime("%Y-%m-%d")}</lastmod><changefreq>daily</changefreq></url>'
sitemap_xml += '</urlset>'
with open("sitemap.xml", "w") as f: f.write(sitemap_xml)

print(f"Build Complete. {len(sitemap_urls)} URLs added to sitemap.xml")
