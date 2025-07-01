import os
import time
import threading
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

WEBHOOK = os.getenv("WEB")
ROBLOSECURITY = os.getenv("ROBLOSECURITY")
COOLDOWN = 5  # seconds between checks

HEADERS = {
    "Content-Type": "application/json",
    "Cookie": f".ROBLOSECURITY={ROBLOSECURITY}"
}

USERNAMES = ["9Dcx", "AnotherUsername"]

def get_user_id(username):
    resp = requests.post(
        "https://users.roblox.com/v1/usernames/users",
        json={"usernames": [username], "excludeBannedUsers": False},
        headers=HEADERS
    )
    resp.raise_for_status()
    data = resp.json().get("data", [])
    return data[0]["id"] if data else None

def get_avatar_url(user_id):
    return f"https://www.roblox.com/headshot-thumbnail/image?userId={user_id}&width=150&height=150&format=png"

def check_presence(user_id):
    resp = requests.post(
        "https://presence.roblox.com/v1/presence/users",
        json={"userIds": [user_id]},
        headers=HEADERS
    )
    resp.raise_for_status()
    return resp.json()["userPresences"][0]

def get_game_info(universe_id):
    resp = requests.get(f"https://games.roblox.com/v1/games?universeIds={universe_id}")
    if resp.ok:
        data = resp.json().get("data", [])
        return data[0].get("name") if data else "Unknown Game"
    return "Unknown Game"

def notify_discord(username, user_id, event, status_code, place_id=None, universe_id=None, game_id=None, start_time=None):
    status_texts = ["Offline", "Online", "In Game", "In Studio", "Invisible"]
    status = status_texts[status_code] if status_code < len(status_texts) else f"Status {status_code}"
    now = datetime.utcnow()
    duration = f"{(now - start_time).seconds // 60}m {(now - start_time).seconds % 60}s" if start_time else "N/A"

    fields = [
        {"name": "Event", "value": event, "inline": True},
        {"name": "Status", "value": status, "inline": True},
        {"name": "Since", "value": start_time.strftime('%Y-%m-%d %H:%M:%S UTC') if start_time else "N/A", "inline": False},
        {"name": "Session Duration", "value": duration, "inline": True}
    ]

    if place_id:
        game_url = f"https://www.roblox.com/games/{place_id}"
        fields.append({"name": "Game Link", "value": f"[Join Game]({game_url})", "inline": False})

    if universe_id:
        game_name = get_game_info(universe_id)
        fields.append({"name": "Game Name", "value": game_name, "inline": True})

    if game_id:
        join_link = f"roblox://experiences/start?placeId={place_id}&gameId={game_id}"
        fields.append({"name": "Join Server", "value": join_link, "inline": False})
        fields.append({"name": "Server ID", "value": game_id, "inline": True})

    embed = {
        "title": f"🔔 {username} Update",
        "color": 0x00ff00 if status_code != 0 else 0xff0000,
        "fields": fields,
        "footer": {"text": "Roblox Tracker"},
        "thumbnail": {"url": get_avatar_url(user_id)},
        "timestamp": now.isoformat()
    }

    requests.post(WEBHOOK, json={"embeds": [embed]})

def monitor_user(username):
    user_id = get_user_id(username)
    if not user_id:
        print(f"❌ Could not find user: {username}")
        return

    last_status, last_game, last_game_id = None, None, None
    start_time = None

    while True:
        try:
            data = check_presence(user_id)
            status = data.get("userPresenceType", 0)
            place_id = data.get("placeId")
            universe_id = data.get("universeId")
            game_id = data.get("gameId")

            changed = (status != last_status or place_id != last_game or game_id != last_game_id)

            if changed:
                event = "Status Update"
                if status == 2 and place_id:
                    event = "Joined Game"
                elif status == 0:
                    event = "Went Offline"
                elif status == 1:
                    event = "Online on Website"
                elif status == 3:
                    event = "In Studio"

                notify_discord(username, user_id, event, status, place_id, universe_id, game_id, start_time or datetime.utcnow())

                last_status = status
                last_game = place_id
                last_game_id = game_id
                start_time = datetime.utcnow()

        except Exception as e:
            print(f"Error tracking {username}: {e}")

        time.sleep(COOLDOWN)

if __name__ == "__main__":
    for user in USERNAMES:
        threading.Thread(target=monitor_user, args=(user,), daemon=True).start()
    while True:
        time.sleep(60)
