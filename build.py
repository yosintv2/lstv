import json, os, re, glob, logging
from datetime import datetime, timedelta
from xml.etree.ElementTree import Element, SubElement, tostring

# --- INITIAL SETTINGS ---
DOMAIN = "https://tv.cricfoot.net"
INPUT_DIR = "date"
OUTPUT_DIR = "output"
DATE_NOW = datetime.now().date()

# Define Week: Starts Friday, Ends Thursday
friday_offset = (DATE_NOW.weekday() - 4) % 7
CURRENT_FRIDAY = DATE_NOW - timedelta(days=friday_offset)
WEEK_DATES = [CURRENT_FRIDAY + timedelta(days=i) for i in range(7)]

logging.basicConfig(level=logging.INFO, format='%(message)s')

class FootballGenerator:
    def __init__(self):
        self.matches = []
        self.channels_index = {}
        self.urls = [DOMAIN + "/"]
        self.load_templates()
        self.load_match_data()

    def load_templates(self):
        self.temps = {}
        for t in ['home', 'match', 'channel']:
            with open(f'{t}_template.html', 'r', encoding='utf-8') as f:
                self.temps[t] = f.read()

    def load_match_data(self):
        for f in glob.glob(f"{INPUT_DIR}/*.json"):
            with open(f, 'r', encoding='utf-8') as j:
                self.matches.extend(json.load(j))

    def clean_url(self, text):
        return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')

    def build_match_pages(self):
        logging.info("Building Match Folders...")
        for m in self.matches:
            k_dt = datetime.fromtimestamp(m['kickoff'])
            m_slug = self.clean_url(m['fixture'])
            m_date_dir = k_dt.strftime('%Y%m%d')
            
            # Create Path: output/match/arsenal-vs-liverpool/20260111/
            full_path = f"{OUTPUT_DIR}/match/{m_slug}/{m_date_dir}"
            os.makedirs(full_path, exist_ok=True)
            
            rows = ""
            for c_data in m.get('tv_channels', []):
                pills = ""
                for ch in c_data['channels']:
                    pills += f'<a href="{DOMAIN}/channel/{self.clean_url(ch)}/" class="ch-link">{ch}</a>'
                    self.channels_index.setdefault(ch, []).append(m)
                
                rows += f'<tr><td class="country-name">{c_data["country"]}</td><td class="channel-pills">{pills}</td></tr>'

            m_html = self.temps['match'].replace("{{FIXTURE}}", m['fixture'])\
                                     .replace("{{TIME}}", k_dt.strftime('%H:%M'))\
                                     .replace("{{VENUE}}", m.get('venue', 'Global Stadium'))\
                                     .replace("{{LEAGUE}}", m.get('league', 'Soccer Match'))\
                                     .replace("{{BROADCAST_ROWS}}", rows)\
                                     .replace("{{DOMAIN}}", DOMAIN)\
                                     .replace("{{DATE}}", k_dt.strftime('%d %b %Y'))
            
            with open(f"{full_path}/index.html", "w", encoding='utf-8') as f:
                f.write(m_html)
            self.urls.append(f"{DOMAIN}/match/{m_slug}/{m_date_dir}/")

    def build_daily_schedule(self):
        logging.info("Building Daily Pages (Fri-Thu)...")
        for day in WEEK_DATES:
            day_str = day.strftime('%Y-%m-%d')
            is_today = (day == DATE_NOW)
            fname = "index.html" if is_today else f"{day_str}.html"
            
            # Weekly Nav Bar
            menu_html = ""
            for d in WEEK_DATES:
                active = "active-day" if d == day else ""
                d_url = f"{DOMAIN}/" if d == DATE_NOW else f"{DOMAIN}/{d.strftime('%Y-%m-%d')}.html"
                menu_html += f'<a href="{d_url}" class="date-item {active}"><div>{d.strftime("%a")}</div>{d.strftime("%b %d")}</a>'

            # Filter Matches
            day_m = [m for m in self.matches if datetime.fromtimestamp(m['kickoff']).date() == day]
            day_m.sort(key=lambda x: (x.get('league') != "Premier League", x['kickoff']))

            listing = ""
            current_league = ""
            for m in day_m:
                league = m.get('league', 'World Football')
                if league != current_league:
                    listing += f'<div class="league-hdr">{league}</div>'
                    current_league = league
                
                m_slug, m_date_id = self.clean_url(m['fixture']), datetime.fromtimestamp(m['kickoff']).strftime('%Y%m%d')
                time_str = datetime.fromtimestamp(m['kickoff']).strftime('%H:%M')
                listing += f'<a href="{DOMAIN}/match/{m_slug}/{m_date_id}/" class="match-row"><div class="m-time">{time_str}</div><div class="m-fixture">{m["fixture"]}</div></a>'

            page = self.temps['home'].replace("{{MATCH_LISTING}}", listing)\
                                   .replace("{{WEEKLY_MENU}}", menu_html)\
                                   .replace("{{DOMAIN}}", DOMAIN)\
                                   .replace("{{PAGE_TITLE}}", f"Live Football TV Guide - {day.strftime('%A')}")
            
            with open(f"{OUTPUT_DIR}/{fname}", "w", encoding='utf-8') as f:
                f.write(page)
            if not is_today: self.urls.append(f"{DOMAIN}/{day_str}.html")

    def build_channel_pages(self):
        logging.info("Building Channel Pages...")
        for ch, ms in self.channels_index.items():
            slug = self.clean_url(ch)
            c_path = f"{OUTPUT_DIR}/channel/{slug}"
            os.makedirs(c_path, exist_ok=True)
            
            listing = ""
            for m in sorted(ms, key=lambda x: x['kickoff']):
                m_slug, m_date_id = self.clean_url(m['fixture']), datetime.fromtimestamp(m['kickoff']).strftime('%Y%m%d')
                listing += f'<a href="{DOMAIN}/match/{m_slug}/{m_date_id}/" class="match-row"><div class="m-time">{datetime.fromtimestamp(m["kickoff"]).strftime("%b %d")}</div><div class="m-fixture">{m["fixture"]}</div></a>'
            
            c_html = self.temps['channel'].replace("{{CHANNEL_NAME}}", ch).replace("{{MATCH_LISTING}}", listing).replace("{{DOMAIN}}", DOMAIN)
            with open(f"{c_path}/index.html", "w", encoding='utf-8') as f:
                f.write(c_html)
            self.urls.append(f"{DOMAIN}/channel/{slug}/")

    def build_sitemap(self):
        logging.info("Building Sitemap...")
        root = Element('urlset', xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
        for u in self.urls:
            url = SubElement(root, 'url')
            SubElement(url, 'loc').text = u
            SubElement(url, 'changefreq').text = "daily"
        
        with open(f"{OUTPUT_DIR}/sitemap.xml", "wb") as f:
            f.write(tostring(root))

    def run(self):
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        self.build_match_pages()
        self.build_daily_schedule()
        self.build_channel_pages()
        self.build_sitemap()
        logging.info("DONE!")

if __name__ == "__main__":
    FootballGenerator().run()
