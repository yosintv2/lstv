import json, os, re, glob, logging
from datetime import datetime, timedelta
from xml.etree.ElementTree import Element, SubElement, tostring

# --- CONFIG ---
DOMAIN = "https://tv.cricfoot.net"
INPUT_FOLDER = "date"
OUTPUT_FOLDER = "public"
TOP_LEAGUES = ["Premier League", "Champions League", "La Liga", "Serie A"]

logging.basicConfig(level=logging.INFO, format='%(message)s')

class SoccerGenerator:
    def __init__(self):
        self.matches = []
        self.channels_db = {}
        self.sitemap_urls = [f"{DOMAIN}/"]
        # Ensure directories exist
        for d in [INPUT_FOLDER, OUTPUT_FOLDER]:
            if not os.path.exists(d): os.makedirs(d)

    def slugify(self, text):
        return re.sub(r'[^a-z0-9]+', '-', str(text).lower()).strip('-')

    def load_templates(self):
        # Explicitly checking paths to prevent "FileNotFound" errors
        temps = {}
        for t in ['home', 'match', 'channel']:
            path = f"{t}_template.html"
            if not os.path.exists(path):
                # Fallback: create a basic template if missing to prevent crash
                logging.warning(f"Warning: {path} not found. Using fallback.")
                temps[t] = "<html><body>{{MATCH_LISTING}}{{BROADCAST_ROWS}}{{LISTING}}</body></html>"
            else:
                with open(path, 'r', encoding='utf-8') as f:
                    temps[t] = f.read()
        return temps

    def run(self):
        temps = self.load_templates()
        
        # Load JSON files
        for f_path in glob.glob(f"{INPUT_FOLDER}/*.json"):
            try:
                with open(f_path, 'r', encoding='utf-8') as f:
                    self.matches.extend(json.load(f))
            except Exception as e:
                logging.error(f"Error loading {f_path}: {e}")

        if not self.matches:
            logging.error("No matches found in /date folder! Build halted.")
            return

        # 1. Generate Match Pages
        for m in self.matches:
            k_dt = datetime.fromtimestamp(m['kickoff'])
            slug = self.slugify(m['fixture'])
            date_id = k_dt.strftime('%Y%m%d')
            path = os.path.join(OUTPUT_FOLDER, "match", slug, date_id)
            os.makedirs(path, exist_ok=True)

            rows = ""
            for country in m.get('tv_channels', []):
                pills = "".join([f'<a href="{DOMAIN}/channel/{self.slugify(ch)}/" class="ch-link" style="margin-right:5px; color:blue;">{ch}</a>' for ch in country['channels']])
                rows += f'<tr><td style="padding:10px; border-bottom:1px solid #eee;"><b>{country["country"]}</b></td><td>{pills}</td></tr>'
                for ch in country['channels']: self.channels_db.setdefault(ch, []).append(m)

            m_html = temps['match'].replace("{{FIXTURE}}", m['fixture']).replace("{{TIME_UNIX}}", str(m['kickoff'])).replace("{{LEAGUE}}", m.get('league', 'Soccer')).replace("{{VENUE}}", m.get('venue', 'TBA')).replace("{{BROADCAST_ROWS}}", rows).replace("{{DOMAIN}}", DOMAIN)
            with open(os.path.join(path, "index.html"), "w", encoding='utf-8') as f: f.write(m_html)
            self.sitemap_urls.append(f"{DOMAIN}/match/{slug}/{date_id}/")

        # 2. Daily Pages (Fri-Thu)
        today = datetime.now().date()
        friday = today - timedelta(days=(today.weekday() - 4) % 7)
        week = [friday + timedelta(days=i) for i in range(7)]

        for day in week:
            day_str = day.strftime('%Y-%m-%d')
            nav = "".join([f'<a href="{DOMAIN}/' + ('' if d == today else d.strftime('%Y-%m-%d')) + f'" class="date-tab {"active-day" if d == day else ""}" style="padding:10px; border:1px solid #ccc;">{d.strftime("%a %d")}</a>' for d in week])
            
            day_m = [m for m in self.matches if datetime.fromtimestamp(m['kickoff']).date() == day]
            day_m.sort(key=lambda x: (x.get('league') not in TOP_LEAGUES, x['kickoff']))

            listing = ""
            for m in day_m:
                m_slug = self.slugify(m['fixture'])
                m_date_id = datetime.fromtimestamp(m['kickoff']).strftime('%Y%m%d')
                listing += f'<a href="{DOMAIN}/match/{m_slug}/{m_date_id}/" class="m-row" style="display:flex; padding:10px; border-bottom:1px solid #eee; text-decoration:none; color:black;"><b style="width:60px;">{datetime.fromtimestamp(m["kickoff"]).strftime("%H:%M")}</b><span>{m["fixture"]}</span></a>'

            d_html = temps['home'].replace("{{MATCH_LISTING}}", listing).replace("{{WEEKLY_NAV}}", nav).replace("{{DOMAIN}}", DOMAIN).replace("{{TITLE}}", f"Football Guide {day_str}")
            
            if day == today:
                with open(os.path.join(OUTPUT_FOLDER, "index.html"), "w", encoding='utf-8') as f: f.write(d_html)
            else:
                d_path = os.path.join(OUTPUT_FOLDER, day_str)
                os.makedirs(d_path, exist_ok=True)
                with open(os.path.join(d_path, "index.html"), "w", encoding='utf-8') as f: f.write(d_html)
                self.sitemap_urls.append(f"{DOMAIN}/{day_str}/")

        # 3. Channel Pages
        for name, ms in self.channels_db.items():
            c_slug = self.slugify(name)
            c_path = os.path.join(OUTPUT_FOLDER, "channel", c_slug)
            os.makedirs(c_path, exist_ok=True)
            c_list = "".join([f'<div style="padding:10px; border-bottom:1px solid #eee;">{x["fixture"]}</div>' for x in ms])
            c_html = temps['channel'].replace("{{CHANNEL_NAME}}", name).replace("{{LISTING}}", c_list).replace("{{DOMAIN}}", DOMAIN)
            with open(os.path.join(c_path, "index.html"), "w", encoding='utf-8') as f: f.write(c_html)
            self.sitemap_urls.append(f"{DOMAIN}/channel/{c_slug}/")

        # 4. Sitemap
        root = Element('urlset', xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
        for loc in self.sitemap_urls: SubElement(SubElement(root, 'url'), 'loc').text = loc
        with open(os.path.join(OUTPUT_FOLDER, "sitemap.xml"), "wb") as f: f.write(tostring(root))

if __name__ == "__main__":
    SoccerGenerator().run()
