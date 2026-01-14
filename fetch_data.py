import json, os, requests, time
from datetime import datetime, timedelta

ENDPOINTS = {
    "h2h": "h2h",
    "lineups": "lineups",
    "statistics": "statistics",
    "odds": "provider/1/winning-odds",
    "form": "pregame-form"
}

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}

def fetch_and_save():
    session = requests.Session()
    session.headers.update(HEADERS)
    
    today = datetime.now()
    # We check 4 days (Today + 3)
    target_dates = [(today + timedelta(days=i)).strftime('%Y%m%d') for i in range(4)]

    for date_str in target_dates:
        date_path = f"date/{date_str}.json"
        if not os.path.exists(date_path): continue
            
        with open(date_path, "r", encoding='utf-8') as f:
            matches = json.load(f)

        for m in matches:
            mid = m.get('match_id')
            if not mid: continue
            
            for folder, path in ENDPOINTS.items():
                os.makedirs(f"data/{folder}", exist_ok=True)
                target_file = f"data/{folder}/{date_str}.json"
                
                day_data = {}
                if os.path.exists(target_file):
                    try:
                        with open(target_file, "r", encoding='utf-8') as rf:
                            day_data = json.load(rf)
                    except: day_data = {}

                if str(mid) in day_data: continue

                try:
                    url = f"https://api.sofascore.com/api/v1/event/{mid}/{path}"
                    # SUCCESS KEY: 5-second timeout. If no answer, move to next match.
                    res = session.get(url, timeout=5) 
                    
                    if res.status_code == 200:
                        day_data[str(mid)] = res.json()
                        with open(target_file, "w", encoding='utf-8') as wf:
                            json.dump(day_data, wf)
                    elif res.status_code == 403:
                        print("Rate limited/Blocked. Stopping early to save progress.")
                        return 
                    
                    time.sleep(0.5) # Gentle delay
                except Exception:
                    # If it times out or fails, just skip this specific match
                    continue 

if __name__ == "__main__":
    fetch_and_save()
