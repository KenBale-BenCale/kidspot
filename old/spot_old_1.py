import os
import requests
import threading
import leds
import spotipy
from urllib.parse import urlparse

class SpotInstance:
    def __init__(self, account_prefix, device_name, default_volume=50):
        self.account_prefix = account_prefix
        self.device_name = device_name
        self.default_volume = default_volume
        self.sp = None
        self.device_id = None
        self.lock = threading.Lock()
        self.init_spotify()

    # ---------------------------
    # Initialize Spotify client
    # ---------------------------
    def init_spotify(self):
        # Get credentials from environment
        client_id = os.getenv(f"{self.account_prefix}_account_id")
        client_secret = os.getenv(f"{self.account_prefix}_account_secret")
        refresh_token = os.getenv(f"{self.account_prefix}_account_refresh_token")

        if not refresh_token:
            raise RuntimeError(f"No refresh token set for {self.account_prefix}")

        # Get access token using refresh token (headless)
        token = self.get_access_token(client_id, client_secret, refresh_token)
        self.sp = spotipy.Spotify(auth=token)

        # Ensure device is active
        if self.refresh_device():
            print(f"✅ Device {self.device_name} detected for account {self.account_prefix}")
        else:
            print(f"⚠️ Device {self.device_name} not detected for account {self.account_prefix}")
            leds.blink_led("red", duration=3)

    # ---------------------------
    # Refresh access token using refresh_token
    # ---------------------------
    def get_access_token(self, client_id, client_secret, refresh_token):
        url = "https://accounts.spotify.com/api/token"
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": client_id,
            "client_secret": client_secret
        }
        resp = requests.post(url, data=payload)
        if resp.status_code != 200:
            raise RuntimeError(f"Failed to get access token: {resp.text}")
        return resp.json()["access_token"]

    # ---------------------------
    # Refresh device_id dynamically
    # ---------------------------
    def refresh_device(self):
        """Scan available devices for our target device"""
        try:
            devices = self.sp.devices()["devices"]
            for d in devices:
                if d["name"] == self.device_name:
                    self.device_id = d["id"]
                    return True
            self.device_id = None
            return False
        except Exception as e:
            print(f"❌ Error fetching devices ({self.account_prefix}): {e}")
            leds.blink_led("red", duration=2)
            return False

    # ---------------------------
    # Playback control
    # ---------------------------
    def play_url(self, url):
        with self.lock:
            if not getattr(self, "device_id", None) or not self.refresh_device():
                print(f"⚠️ Device {self.device_name} not available for playback")
                leds.blink_led("red", duration=2)
                return

            try:
                # Spotify requires context_uri for playlists/albums, or uris for tracks
                if url.startswith("spotify:") or url.startswith("https://open.spotify.com/"):
                    self.sp.start_playback(device_id=self.device_id, context_uri=url)
                else:
                    print(f"⚠️ Invalid Spotify URL: {url}")
                    leds.blink_led("red", duration=2)
            except Exception as e:
                print(f"❌ Spotify playback error ({self.account_prefix}): {e}")
                leds.blink_led("red", duration=2)

    def pause(self):
        with self.lock:
            try:
                self.sp.pause_playback(device_id=self.device_id)
            except Exception as e:
                print(f"❌ Spotify pause error ({self.account_prefix}): {e}")
                leds.blink_led("red", duration=2)

    def toggle_play_pause(self):
        with self.lock:
            try:
                playback = self.sp.current_playback()
                if playback and playback["is_playing"]:
                    self.sp.pause_playback(device_id=self.device_id)
                else:
                    self.sp.start_playback(device_id=self.device_id)
            except Exception as e:
                print(f"❌ Toggle playback error ({self.account_prefix}): {e}")
                leds.blink_led("red", duration=2)

    def next_track(self):
        with self.lock:
            try:
                self.sp.next_track(device_id=self.device_id)
            except Exception as e:
                print(f"❌ Next track error ({self.account_prefix}): {e}")
                leds.blink_led("red", duration=2)

    def previous_track(self):
        with self.lock:
            try:
                self.sp.previous_track(device_id=self.device_id)
            except Exception as e:
                print(f"❌ Previous track error ({self.account_prefix}): {e}")
                leds.blink_led("red", duration=2)

    def set_volume(self, volume_percent):
        """Set volume 0-100%"""
        with self.lock:
            try:
                self.sp.volume(volume_percent, device_id=self.device_id)
            except Exception as e:
                print(f"❌ Volume set error ({self.account_prefix}): {e}")
                leds.blink_led("red", duration=2)
