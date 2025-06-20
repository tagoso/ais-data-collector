import websocket
import json
import os
import subprocess
from datetime import datetime
from dotenv import load_dotenv

# === Load env. variable ===
load_dotenv()  # Will be ignored by Render

API_KEY = os.environ.get("AISSTREAM_API_KEY")
MMSI_TARGET = os.environ.get("TARGET_MMSI")
DATA_FILE = "data.json"
REPO_DIR = os.path.dirname(os.path.abspath(__file__))

# === Read and write  ===
def load_existing_data():
    try:
        with open(os.path.join(REPO_DIR, DATA_FILE), "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_data(data):
    with open(os.path.join(REPO_DIR, DATA_FILE), "w") as f:
        json.dump(data, f, indent=2)

# === Manage Git ===
def git_push():
    subprocess.run(["git", "add", DATA_FILE], cwd=REPO_DIR)
    subprocess.run(["git", "commit", "-m", f"Update {datetime.utcnow().isoformat()}"], cwd=REPO_DIR)
    subprocess.run(["git", "push"], cwd=REPO_DIR)

# === Handle WebSocket ===
def on_message(ws, message):
    try:
        data = json.loads(message)
        if data.get("MMSI") == MMSI_TARGET:
            print(f"Matched MMSI: {MMSI_TARGET}")
            entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "lat": data.get("LAT"),
                "lon": data.get("LON"),
                "speed": data.get("SPEED"),
                "course": data.get("COURSE")
            }
            existing = load_existing_data()
            existing.append(entry)
            save_data(existing)
            git_push()
    except Exception as e:
        print("Error processing message:", e)

def on_open(ws):
    ws.send(json.dumps({
        "APIKey": API_KEY
    }))
    print("WebSocket connection opened")

def on_error(ws, error):
    print("WebSocket error:", error)

def on_close(ws, close_status_code, close_msg):
    print("WebSocket connection closed")

# === Execution ===
if __name__ == "__main__":
    if not API_KEY:
        print("ERROR: AISSTREAM_API_KEY is not set!")
        exit(1)

    ws = websocket.WebSocketApp(
        "wss://stream.aisstream.io/v0/stream",
        on_message=on_message,
        on_open=on_open,
        on_error=on_error,
        on_close=on_close
    )
    ws.run_forever()