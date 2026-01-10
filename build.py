import json, os, re, glob
from datetime import datetime, timedelta

DOMAIN = "https://tv.cricfoot.net"
DATE_FOLDER = "date/*.json"

def slugify(t): return re.sub(r'[^a-z0-9]+', '-', t.lower()).strip('-')

# 1. SMART MERGE: Remove duplicates and filter by window (Yesterday to Tomorrow)
all_matches = {}
today_dt = datetime.now()
start_window = (today_dt - timedelta(days=1)).replace(hour=0, minute=0, second=0)
end_window = (today_dt + timedelta(days=1)).replace(hour=23, minute=59, second=59)

for file_path in glob.glob(DATE_FOLDER):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            for m in data:
                # Use matchId as primary key, fallback to fixture+time
                uid = str(m.get('matchId') or f"{m['fixture']}-{m['kickoff']}")
                m_time = datetime.fromtimestamp(m['kickoff'])
                
                # Only include matches in our 3-day window
                if start_window <= m_time <= end_window:
                    if uid not in all_matches:
                        all_matches[uid] = m
    except Exception as e: print(f"Error loading {file_path}: {e}")

matches = sorted(all_matches.values(), key=lambda x: x['kickoff'])

# 2. SHARED ASSETS GENERATOR (Menu & Footer)
def get_shared_nav(active_idx=0):
    menu = ""
    for i, label in enumerate(["Yesterday", "Today", "Tomorrow"]):
        d = today_dt + timedelta(days=i-1)
        active = "bg-[#00a0e9] text-white shadow-lg" if i == active_idx else "bg-slate-800 text-slate-400 hover:text-white"
        menu += f'<a href="/" class="flex-1 text-center py-2 rounded-lg text-[10px] font-black uppercase transition {active}">{label}<br><span class="opacity-70">{d.strftime("%b %d")}</span></a>'
    return menu

footer_html = f"""
<footer class="bg-[#001529] text-slate-500 py-12 px-6 mt-12 border-t border-slate-800">
    <div class="max-w-6xl mx-auto grid grid-cols-2 md:grid-cols-4 gap-8 mb-10">
        <div><h4 class="text-white font-black text-xs uppercase mb-4">Explore</h4>
            <ul class="space-y-2 text-sm">
                <li><a href="/" class="hover:text-[#00a0e9]">Home Schedule</a></li>
                <li><a href="/live-now/" class="hover:text-[#00a0e9]">Live Now</a></li>
            </ul>
        </div>
        <div><h4 class="text-white font-black text-xs uppercase mb-4">Channels</h4>
            <ul class="space-y-2 text-sm">
                <li><a href="/channel/sky-sports/" class="hover:text-[#00a0e9]">Sky Sports</a></li>
                <li><a href="/channel/bein-sports/" class="hover:text-[#00a0e9]">beIN Sports</a></li>
            </ul>
        </div>
        <div><h4 class="text-white font-black text-xs uppercase mb-4">Competitions</h4>
            <ul class="space-y-2 text-sm">
                <li><a href="/league/premier-league/" class="hover:text-[#00a0e9]">Premier League</a></li>
                <li><a href="/league/la-liga/" class="hover:text-[#00a0e9]">La Liga</a></li>
            </ul>
        </div>
    </div>
    <div class="text-center text-[10px] uppercase tracking-widest border-t border-slate-800 pt-8">
        &copy; 2026 CricFoot TV • <a href="/privacy/">Privacy</a> • <a href="/terms/">Terms</a>
    </div>
</footer>"""

# 3. PAGE GENERATION (Home, Match, Channel)
# ... [Logic from previous steps remains, but now injects get_shared_nav() and footer_html]
