import json, os, re, glob, logging
from datetime import datetime, timedelta
from xml.etree.ElementTree import Element, SubElement, tostring

# --- CONFIGURATION ---
DOMAIN = "https://tv.cricfoot.net"
INPUT_FOLDER = "date"
OUTPUT_FOLDER = "public"
# Specific League IDs to prioritize (Serie A & Premier League usually)
PRIORITY_LEAGUE_IDS = [23, 17] 

logging.basicConfig(level=logging.INFO, format='%(message)s')

class SoccerGenerator:
    def __init__(self):
        self.matches = []
        self.channels_db = {}
        self.sitemap_urls = [f"{DOMAIN}/"]
        for d in [INPUT_FOLDER, OUTPUT_FOLDER]:
            os.makedirs(d, exist_ok=True)

    def slugify(self, text):
        return re.sub(r'[^a-z0-9]+', '-', str(text).lower()).strip('-')

    def run(self):
        # 1. Load Templates
        try:
            with open('home_template.html', 'r', encoding='utf-8') as f: home_t = f.read()
            with open('match_template.html', 'r', encoding='utf-8') as f: match_t = f.read()
            with open('channel_template.html', 'r', encoding='utf-8') as f: channel_t = f.read()
        except FileNotFoundError as e:
            logging.error(f"Error: Template file not found: {e}")
            return

        # 2. Load and Sort Match Data
        for f_path in glob.glob(f"{INPUT_FOLDER}/*.json"):
            with open(f_path, 'r', encoding='utf-8') as f:
                self.matches.extend(json.load(f))
        
        # Priority Sort Logic:
        # 1st criteria: Is the league_id in our priority list? (0 = Yes, 1 = No)
        # 2nd criteria: Kickoff time
        self.matches.sort(key=lambda x: (x.get('league_id') not in PRIORITY_LEAGUE_IDS, x['kickoff']))

        # 3. Build Folders and Pages
        for m in self.matches:
            m_dt = datetime.fromtimestamp(m['kickoff'])
            m_slug = self.slugify(m['fixture'])
            date_id = m_dt.strftime('%Y%m%d')
            
            # Directory Structure: /match/genoa-vs-cagliari/20260111/index.html
            m_dir = os.path.join(OUTPUT_FOLDER, "match", m_slug, date_id)
            os.makedirs(m_dir, exist_ok=True)

            # Match Page Broadcaster Rows
            rows = ""
            for item in m.get('tv_channels', []):
                pills = "".join([f'<a href="{DOMAIN}/channel/{self.slugify(ch)}/" class="ch-pill">{ch}</a>' for ch in item['channels']])
                rows += f'<tr><td class="country-cell">{item["country"]}</td><td class="channel-cell">{pills}</td></tr>'
                for ch in item['channels']: self.channels_db.setdefault(ch, []).append(m)

            m_html = match_t.replace("{{FIXTURE}}", m['fixture'])\
                            .replace("{{TIME_UNIX}}", str(m['kickoff']))\
                            .replace("{{LEAGUE}}", m.get('league', 'Soccer'))\
                            .replace("{{VENUE}}", m.get('venue', 'TBA'))\
                            .replace("{{BROADCAST_ROWS}}", rows)\
                            .replace("{{DOMAIN}}", DOMAIN)
            
            with open(os.path.join(m_dir, "index.html"), "w", encoding='utf-8') as f: f.write(m_html)
            self.sitemap_urls.append(f"{DOMAIN}/match/{m_slug}/{date_id}/")

        # 4. Generate Main Index
        listing = ""
        last_league = ""
        for m in self.matches:
            if m['league'] != last_league:
                listing += f'<div class="league-header" data-id="{m.get("league_id")}"> {m["league"]}</div>'
                last_league = m['league']
            
            m_slug = self.slugify(m['fixture'])
            date_id = datetime.fromtimestamp(m['kickoff']).strftime('%Y%m%d')
            listing += f'''
            <a href="{DOMAIN}/match/{m_slug}/{date_id}/" class="match-row">
                <div class="match-time" data-unix="{m['kickoff']}"></div>
                <div class="match-info">{m['fixture']}</div>
            </a>'''

        final_home = home_t.replace("{{MATCH_LISTING}}", listing)\
                           .replace("{{DOMAIN}}", DOMAIN)\
                           .replace("{{PAGE_TITLE}}", "Live Soccer TV Guide")\
                           .replace("{{WEEKLY_MENU}}", "") # Add date-switching buttons here

        with open(os.path.join(OUTPUT_FOLDER, "index.html"), "w", encoding='utf-8') as f: f.write(final_home)

        # 5. Build Sitemap
        root = Element('urlset', xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
        for loc in self.sitemap_urls: SubElement(SubElement(root, 'url'), 'loc').text = loc
        with open(os.path.join(OUTPUT_FOLDER, "sitemap.xml"), "wb") as f: f.write(tostring(root))
        logging.info("Site built successfully with league ID prioritization.")

if __name__ == "__main__":
    SoccerGenerator().run()
