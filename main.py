import time
import threading
import requests
from dotenv import load_dotenv
import os
from keep_alive import keep_alive

load_dotenv()

DISCORD_WEBHOOK = os.getenv("WEB")
ROBLOSECURITY = os.getenv("ROBLOSECURITY")
COOLDOWN = 5  # seconds

HEADERS = {
    "Content-Type": "application/json",
    "Cookie": f".ROBLOSECURITY={ROBLOSECURITY}"
}

# List of usernames to monitor
USERNAMES = ["9Dcx", "mwaochaa", "cunyimageholder"]

def get_user_id(username):
    try:
        response = requests.post(
            "https://users.roblox.com/v1/usernames/users",
            json={"usernames": [username]},
            headers=HEADERS
        )
        response.raise_for_status()
        data = response.json()
        return data["data"][0]["id"] if data["data"] else None
    except Exception as e:
        print(f"Failed to get user ID for {username}:", e)
        return None

def check_presence(user_id):
    response = requests.post(
        "https://presence.roblox.com/v1/presence/users",
        json={"userIds": [user_id]},
        headers=HEADERS
    )
    response.raise_for_status()
    return response.json()["userPresences"][0]

def notify_discord(username, status_code, place_id=None, event_type="Status Changed"):
    status_names = ["Offline", "Online on Website", "In Game", "In Studio", "Invisible"]
    status = status_names[status_code] if status_code < len(status_names) else f"Unknown ({status_code})"

    embed = {
        "title": f"{username} - {event_type}",
        "color": 0x00ff00 if status_code != 0 else 0xff0000,
        "fields": [{"name": "Status", "value": status, "inline": True}],
        "footer": {"text": "Roblox Activity Tracker"}
    }

    if status_code == 2 and place_id:
        game_url = f"https://www.roblox.com/games/{place_id}"
        embed["fields"].append({
            "name": "Game Link",
            "value": f"[Click to Join Game]({game_url})",
            "inline": False
        })

    try:
        requests.post(DISCORD_WEBHOOK, json={"embeds": [embed]})
        print(f"🔔 {username} - {event_type}: {status} (placeId={place_id})")
    except Exception as e:
        print("Failed to send Discord webhook:", e)

def monitor_user(username):
    user_id = get_user_id(username)
    if not user_id:
        print(f"❌ User {username} not found.")
        return

    last_status = None
    last_place = None

    while True:
        try:
            presence = check_presence(user_id)
            status = presence.get("userPresenceType", 0)
            place_id = presence.get("placeId")

            if status != last_status or place_id != last_place:
                event = "Status Changed"
                if status == 0:
                    event = "User Went Offline"
                elif last_status == 0 and status != 0:
                    event = "User Came Online"
                elif place_id and place_id != last_place:
                    event = "Joined New Game"

                notify_discord(username, status, place_id, event_type=event)
                last_status = status
                last_place = place_id

        except Exception as e:
            print(f"Monitor Error for {username}:", e)

        time.sleep(COOLDOWN)

if __name__ == "__main__":
    keep_alive()
    for username in USERNAMES:
        threading.Thread(target=monitor_user, args=(username,)).start()
