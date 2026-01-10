import json, os, re, glob, time
from datetime import datetime, timedelta

# jan 11, 2026 is today
TODAY = datetime(2026, 1, 11).date()
TOMORROW = TODAY + timedelta(days=1)

def slugify(t): return re.sub(r'[^a-z0-9]+', '-', t.lower()).strip('-')

# Load and Deduplicate
all_matches = {}
for file_path in glob.glob("date/*.json"):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for m in json.load(f):
                uid = f"{m['fixture']}-{m['kickoff']}"
                if uid not in all_matches: all_matches[uid] = m
    except: pass

# Templates
with open('home_template.html', 'r') as f: home_temp = f.read()
with open('match_template.html', 'r') as f: match_temp = f.read()
with open('channel_template.html', 'r') as f: chan_temp = f.read()

channels_data = {}

# Generate Match Pages
for m in all_matches.values():
    m_dt = datetime.fromtimestamp(m['kickoff'])
    m_date = m_dt.date()
    
    # Process only Today and Tomorrow
    if m_date in [TODAY, TOMORROW]:
        slug = slugify(m['fixture'])
        date_str = m_dt.strftime('%Y%m%d')
        path = f"match/{slug}/{date_str}"
        os.makedirs(path, exist_ok=True)
        
        # Build Table Rows
        rows, top_ch = "", []
        for c in m.get('tv_channels', []):
            pills = "".join([f'<a href="/channel/{slugify(ch)}/" class="pill">{ch}</a>' for ch in c['channels']])
            rows += f'<div class="row"><div class="c-name">{c["country"]}</div><div class="ch-list">{pills}</div></div>'
            top_ch.extend(c['channels'])
            # Store channel data for channel pages
            for ch in c['channels']:
                channels_data.setdefault(ch, []).append(m)

        # Write Match Page
        m_html = match_temp.replace("{{FIXTURE}}", m['fixture']).replace("{{TIME}}", m_dt.strftime('%H:%M'))\
                           .replace("{{DATE}}", m_dt.strftime('%d %b %Y')).replace("{{BROADCAST_ROWS}}", rows)\
                           .replace("{{LEAGUE}}", m.get('league', 'Football'))
        with open(f"{path}/index.html", "w") as f: f.write(m_html)

# Generate Channel Pages
for ch_name, m_list in channels_data.items():
    path = f"channel/{slugify(ch_name)}"
    os.makedirs(path, exist_ok=True)
    list_html = "".join([f'<a href="/match/{slugify(x["fixture"])}/{datetime.fromtimestamp(x["kickoff"]).strftime("%Y%m%d")}/" class="match-card"><div class="time-col">{datetime.fromtimestamp(x["kickoff"]).strftime("%H:%M")}</div><div>{x["fixture"]}</div></a>' for x in m_list])
    c_html = chan_temp.replace("{{CHANNEL_NAME}}", ch_name).replace("{{MATCH_LISTING}}", list_html)
    with open(f"{path}/index.html", "w") as f: f.write(c_html)
