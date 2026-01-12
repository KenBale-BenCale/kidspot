# buttons.py
import threading
import RPi.GPIO as GPIO
import time
import logging

log = logging.getLogger("Buttons")

# ---------------------------
# Configuration
# ---------------------------
BUTTON_PINS = {
    "play": 5,
    "next": 6,
    "prev": 13,
    "volu": 20,
    "vold": 26
}

vol_step = 5  # % increment for Spotify volume

# Internal state
_stop_listener = False
_listener_thread = None
_last_prev_press = 0
_prev_press_count = 0

# ---------------------------
# Helper functions
# ---------------------------
def _toggle_play(spot_instance):
    if not spot_instance:
        return
    playback = spot_instance.get_current_playback()
    if playback and playback.get("is_playing", False):
        spot_instance.pause()
    else:
        if playback and playback.get("item"):
            spot_instance.play_url(playback["item"]["uri"])
        else:
            log.info("Play pressed but no track available")

def _next_track(spot_instance):
    """Send Spotify API call to skip to the next track"""
    if spot_instance and spot_instance.sp and spot_instance.device_id:
        try:
            spot_instance.sp.next_track(device_id=spot_instance.device_id)
            log.info("Next track triggered")
        except Exception as e:
            log.warning(f"Next track error: {e}")

def _prev_track(spot_instance):
    """Send Spotify API call to skip to the previous track"""
    if spot_instance and spot_instance.sp and spot_instance.device_id:
        try:
            spot_instance.sp.previous_track(device_id=spot_instance.device_id)
            log.info("Previous track triggered")
        except Exception as e:
            log.warning(f"Previous track error: {e}")

def _restart_or_prev(spot_instance):
    """Short press: restart track; double press: previous track"""
    global _last_prev_press, _prev_press_count
    now = time.time()
    if now - _last_prev_press < 0.5:  # double press window
        _prev_press_count += 1
    else:
        _prev_press_count = 1
    _last_prev_press = now

    if _prev_press_count == 2:
        _prev_track(spot_instance)
        _prev_press_count = 0
    else:
        # restart current track
        playback = spot_instance.get_current_playback()
        if playback and playback.get("item"):
            spot_instance.play_url(playback["item"]["uri"])
            log.info("Prev button short press - restart track")

def _vol_up(spot_instance):
    if spot_instance and spot_instance.sp and spot_instance.device_id:
        try:
            playback = spot_instance.get_current_playback()
            if playback:
                current_vol = playback.get("device", {}).get("volume_percent", 50)
                new_vol = min(100, current_vol + vol_step)
                spot_instance.sp.volume(new_vol, device_id=spot_instance.device_id)
                log.info(f"Volume increased to {new_vol}%")
        except Exception as e:
            log.warning(f"Volume up error: {e}")

def _vol_down(spot_instance):
    if spot_instance and spot_instance.sp and spot_instance.device_id:
        try:
            playback = spot_instance.get_current_playback()
            if playback:
                current_vol = playback.get("device", {}).get("volume_percent", 50)
                new_vol = max(0, current_vol - vol_step)
                spot_instance.sp.volume(new_vol, device_id=spot_instance.device_id)
                log.info(f"Volume decreased to {new_vol}%")
        except Exception as e:
            log.warning(f"Volume down error: {e}")

# ---------------------------
# Button listener
# ---------------------------
def _listener(spot_instance):
    global _stop_listener
    while not _stop_listener:
        for name, pin in BUTTON_PINS.items():
            if GPIO.input(pin) == GPIO.LOW:  # pressed
                if name == "play":
                    _toggle_play(spot_instance)
                elif name == "next":
                    _next_track(spot_instance)
                elif name == "prev":
                    _restart_or_prev(spot_instance)
                elif name == "volu":
                    _vol_up(spot_instance)
                elif name == "vold":
                    _vol_down(spot_instance)
                time.sleep(0.3)  # debounce
        time.sleep(0.05)

def button_listener(spot_instance):
    global _stop_listener, _listener_thread
    _stop_listener = False

    GPIO.setmode(GPIO.BCM)
    for pin in BUTTON_PINS.values():
        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    _listener_thread = threading.Thread(target=_listener, args=(spot_instance,), daemon=True)
    _listener_thread.start()
    log.info("Button listener started")

def stop_buttons():
    global _stop_listener, _listener_thread
    _stop_listener = True
    if _listener_thread:
        _listener_thread.join()
    GPIO.cleanup()
    log.info("Button listener stopped")
