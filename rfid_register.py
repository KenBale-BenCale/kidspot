#!/usr/bin/env python3
"""
rfid_uid_editor.py - RFID swipe.json editor

Features:
 - Detects RFID tokens via PN532
 - Reads/writes swipe.json
 - Prompts before overwriting existing entries
 - Prompts for Spotify URL
 - Prompts for structured metadata with enforced keys
"""

import os
import json
import time
import board
import busio
from adafruit_pn532.i2c import PN532_I2C

# ---------------------------
# Config
# ---------------------------
UID_JSON_PATH = "swipe.json"

METADATA_FIELDS = [
    ("Artist", "Artist / Band name"),
    ("Title",  "Track / Playlist title"),
    ("Album",  "Album name"),
    ("Type",   "Type (Track / Album / Playlist / Podcast)"),
    ("Year",   "Release year")
]

# ---------------------------
# PN532 setup (I2C)
# ---------------------------
i2c = busio.I2C(board.SCL, board.SDA)
pn532 = PN532_I2C(i2c, debug=False)
pn532.SAM_configuration()

# ---------------------------
# Load existing data
# ---------------------------
if os.path.exists(UID_JSON_PATH):
    try:
        with open(UID_JSON_PATH, "r") as f:
            uid_map = json.load(f)
    except json.JSONDecodeError:
        print("⚠️ swipe.json is invalid. Starting fresh.")
        uid_map = {}
else:
    uid_map = {}

print(f"Loaded {len(uid_map)} swipe entries.\n")

# ---------------------------
# Helper functions
# ---------------------------
def prompt_metadata():
    """Prompt user for structured metadata"""
    metadata = {}

    print("\nEnter metadata (leave blank to skip a field):")
    for key, description in METADATA_FIELDS:
        value = input(f"  {key} ({description}): ").strip()
        if value:
            metadata[key] = value

    return metadata


def save_json():
    with open(UID_JSON_PATH, "w") as f:
        json.dump(uid_map, f, indent=2)
    print("✅ swipe.json updated.\n")

# ---------------------------
# Main loop
# ---------------------------
try:
    print("Present an RFID token. Press Ctrl+C to exit.\n")

    while True:
        uid = pn532.read_passive_target(timeout=0.5)
        if uid is None:
            continue

        uid_str = "".join("{:02X}".format(b) for b in uid)
        print(f"\n📟 RFID detected: {uid_str}")

        if uid_str in uid_map:
            print("Existing entry:")
            print(json.dumps(uid_map[uid_str], indent=2))
            overwrite = input("Overwrite this entry? (y/n): ").strip().lower()
            if overwrite != "y":
                print("⏭ Skipped.")
                continue

        # ---- URL prompt ----
        url = input("Enter Spotify URL/URI: ").strip()
        if not url:
            print("⚠️ No URL entered. Skipped.")
            continue

        # ---- Metadata prompt ----
        metadata = prompt_metadata()

        # ---- Save entry ----
        uid_map[uid_str] = {
            "URL": url,
            "metadata": metadata
        }

        save_json()
        time.sleep(0.3)

except KeyboardInterrupt:
    print("\n👋 Exiting editor. Goodbye!")
