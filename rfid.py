import board
import busio
from digitalio import DigitalInOut
from adafruit_pn532.i2c import PN532_I2C
import json
import threading
import time
import leds

# I2C setup
i2c = busio.I2C(board.SCL, board.SDA)
pn532 = PN532_I2C(i2c, debug=False)
pn532.SAM_configuration()

# ---------------------------
# Load swipe data
# ---------------------------
with open("swipe.json", "r") as f:
    swipe_data = json.load(f)

# ---------------------------
# Thread control
# ---------------------------
stop_event = threading.Event()

# ---------------------------
# UID handling
# ---------------------------
def handle_uid(uid, spot_instance):
    """Play Spotify item based on swiped UID"""
    try:
        uid_entry = swipe_data.get(uid)
        if not uid_entry:
            print(f"⚠️ Unknown card: {uid}")
            leds.blink_led("red", duration=2)
            return

        url = uid_entry.get("URL")
        if not url:
            print(f"⚠️ No URL set for UID {uid}")
            leds.blink_led("red", duration=2)
            return

        # Pass only the URL string to spot.py
        spot_instance.play_url(url)
        print("Spotify RFID card detected: Playing")
        metadata = uid_entry.get("METADATA", {})
        if metadata:
            metadata_str = " - ".join(f"{v}" for k, v in metadata.items())
            print(f"🎵 Playing: {metadata_str}")
        else:
            print(f"🎵 Playing URL: {url} (no metadata available)")
#        time.sleep(0.1)

    except Exception as e:
        print(f"❌ Error handling UID {uid}: {e}")
        leds.blink_led("red", duration=2)

# ---------------------------
# Listening loop
# ---------------------------
def _listen(spot_instance):
    while not stop_event.is_set():
        uid = pn532.read_passive_target(timeout=0.5)
        if uid:
            # Convert UID from bytes to hex string or whatever format you use
            uid_str = ''.join([f'{x:02X}' for x in uid])
            handle_uid(uid_str, spot_instance)
        time.sleep(0.1)

# ---------------------------
# Public start/stop functions
# ---------------------------
def listener(spot_instance):
    """Start listening thread for RFID swipes"""
    t = threading.Thread(target=_listen, args=(spot_instance,), daemon=True)
    t.start()
    return t

def stop_rfid():
    """Stop the RFID listener"""
    stop_event.set()
