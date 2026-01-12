import threading
import time
import json
import leds
import spot
import os

from digitalio import DigitalInOut
import board
import busio
import adafruit_pn532.i2c

stop_event = threading.Event()

with open("swipe.json", "r") as f:
    swipe_data = json.load(f)

# PN532 setup
i2c = busio.I2C(board.SCL, board.SDA)
pn532 = adafruit_pn532.i2c.PN532_I2C(i2c)
pn532.SAM_configuration()

def read_card():
    try:
        uid_bytes = pn532.read_passive_target(timeout=0.1)
        if uid_bytes:
            return "".join("{:02X}".format(b) for b in uid_bytes)
    except:
        return None

def handle_uid(uid, spot_instance):
    """Play Spotify item based on swiped UID"""
    try:
        uid_data = swipe_data.get(uid)
        if not uid_data:
            print(f"⚠️ Unknown card: {uid}")
            leds.blink_led("red", duration=2)
            return

        url = uid_data.get("URL")  # <-- grab the URL string only
        if not url:
            print(f"⚠️ No URL set for UID {uid}")
            leds.blink_led("red", duration=2)
            return

        spot_instance.play_url(url)  # pass only the string
    except Exception as e:
        print(f"❌ Error handling UID {uid}: {e}")
        leds.blink_led("red", duration=2)


def listener(spot_instance):
    def _listen():
        while not stop_event.is_set():
            uid = read_card()
            if uid:
                handle_uid(uid, spot_instance)
            time.sleep(0.1)
    t = threading.Thread(target=_listen, daemon=True)
    t.start()

def stop_rfid():
    stop_event.set()
