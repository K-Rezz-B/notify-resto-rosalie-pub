#!/usr/bin/env python3
"""Surveille la dispo Zenchef de la Brasserie Rosalie et pousse une notif via ntfy.sh."""
import datetime
import json
import os
import urllib.parse
import urllib.request

RID = os.getenv("RID", "363169")            # ID Zenchef de Brasserie Rosalie
DATE = os.getenv("DATE", "2026-12-24")
GUESTS = int(os.getenv("GUESTS", "7"))
SLOT = os.getenv("SLOT", "20:00")
TOPIC = os.environ["NTFY_TOPIC"]
STATE = os.getenv("STATE_FILE", "state/notified")

API = "https://bookings-middleware.zenchef.com/getAvailabilities"
BOOK_URL = f"https://bookings.zenchef.com/results?rid={RID}&pid=1001"


def fetch():
    q = urllib.parse.urlencode({"restaurantId": RID, "date_begin": DATE, "date_end": DATE})
    req = urllib.request.Request(
        f"{API}?{q}",
        headers={"Accept": "application/json", "User-Agent": "Mozilla/5.0"},
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def find_slot(days):
    for day in days:
        if day.get("date") != DATE:
            continue
        for shift in day.get("shifts", []):
            for slot in shift.get("shift_slots", []):
                if slot.get("name") == SLOT:
                    return slot
    return None


def notify(title, msg, prio="urgent"):
    req = urllib.request.Request(
        f"https://ntfy.sh/{TOPIC}",
        data=msg.encode("utf-8"),
        headers={"Title": title, "Priority": prio, "Tags": "fork_and_knife", "Click": BOOK_URL},
    )
    urllib.request.urlopen(req, timeout=20)


def read_state():
    try:
        return open(STATE).read().strip() == "1"
    except FileNotFoundError:
        return False


def write_state(value):
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    with open(STATE, "w") as f:
        f.write("1" if value else "0")


def main():
    if os.getenv("TEST_NOTIFY") == "1":
        notify("Test Rosalie watcher", "Les notifications fonctionnent ✅", "default")
        return

    if datetime.date.today() > datetime.date.fromisoformat(DATE):
        print("Date passée, rien à faire.")
        return

    slot = find_slot(fetch())
    guests = slot.get("possible_guests", []) if slot else []
    available = GUESTS in guests
    already = read_state()
    print(f"slot {SLOT} trouvé={slot is not None} possible_guests={guests} dispo={available}")

    if available and not already:
        notify(
            f"Table dispo - Rosalie {DATE} {SLOT}",
            f"Créneau {SLOT} ouvert pour {GUESTS} personnes. Tape pour réserver !",
        )
    # Mémorise l'état : 1 seule notif par ouverture, ré-armée si le créneau se referme
    write_state(available)


if __name__ == "__main__":
    main()
