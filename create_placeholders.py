import os
import json
from datetime import datetime, timedelta

def run():
    # Calculate date +2 days from today
    target_date = datetime.now() + timedelta(days=2)
    date_str = target_date.strftime("%Y-%m-%d")
    file_id = target_date.strftime("%Y%m%d")
    file_name = f"{file_id}.json"
    folder = "date"
    
    if not os.path.exists(folder):
        os.makedirs(folder)

    file_path = os.path.join(folder, file_name)

    # Only create if it doesn't exist to avoid overwriting your manual edits
    if not os.path.exists(file_path):
        placeholder = {
            "status": "Enter TV Channels",
            "date": date_str,
            "matches": []
        }
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(placeholder, f, indent=4)
        print(f"CREATED:{file_id}:{date_str}")
    else:
        print(f"EXISTS:{file_id}:{date_str}")

if __name__ == "__main__":
    run()
