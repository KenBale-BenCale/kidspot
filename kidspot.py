# kidspot.py
import os
import leds
import rfid
import buttons
from spot import SpotInstance
from dotenv import load_dotenv
import time
import signal

leds.init_leds()

# ---------------------------
# Load environment
# ---------------------------
load_dotenv()
DEVICE_NAME = os.getenv("device_name")
DEFAULT_VOLUME = int(os.getenv("default_volume", 50))
ACCOUNT_PREFIXES = ["BEN", "NICOLA", "KIDS"]

# ---------------------------
# Multi-account setup
# ---------------------------
spot_instances = {}  # <-- initialize dictionary here

for prefix in ACCOUNT_PREFIXES:
    client_id = os.getenv(f"SPOTIFY_{prefix}_CLIENT_ID")
    client_secret = os.getenv(f"SPOTIFY_{prefix}_CLIENT_SECRET")
    refresh_token = os.getenv(f"SPOTIFY_{prefix}_REFRESH_TOKEN")

    if not (client_id and client_secret and refresh_token):
        print(f"⚠️ Skipping account {prefix} (missing credentials)")
        continue
    try:
        instance = SpotInstance(prefix, DEVICE_NAME, DEFAULT_VOLUME)
        spot_instances[prefix] = instance
    except Exception as e:
        print(f"❌ Failed to initialize Spotify for {prefix}: {e}")

# ---------------------------
# Select first available active account for listeners
# ---------------------------
spot_instance = None
for inst in spot_instances.values():
    if inst.active:
        spot_instance = inst
        break
if spot_instance is None and spot_instances:
    # fallback to first available account
    spot_instance = next(iter(spot_instances.values()))

# ---------------------------
# Start other components
# ---------------------------
rfid.listener(spot_instance)
buttons.button_listener(spot_instance)

# ---------------------------
# Test LEDs
# ---------------------------
for color in ["red", "yellow", "green"]:
    leds.turn_on_led(color)
time.sleep(1)
for color in ["red", "yellow", "green"]:
    leds.turn_off_led(color)

# ---------------------------
# Shutdown handling
# ---------------------------
def shutdown(signal_received, frame):
    print("Shutting down Kidspot...")
    rfid.stop_rfid()
    buttons.stop_buttons()
    leds.shutdown_leds()
    exit(0)

signal.signal(signal.SIGINT, shutdown)

# ---------------------------
# Keep main thread alive
# ---------------------------
print("🟢 Kidspot running. Waiting for events...")

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("🛑 Shutdown requested")
    leds.shutdown_leds()
