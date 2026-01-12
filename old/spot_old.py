import os
import time
import spotipy
import leds
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
import requests
import threading

class SpotInstance:
    def __init__(self, account_prefix, device_name, default_volume=50):
        self.account_prefix = account_prefix
        self.device_name = device_name
        self.default_volume = default_volume
        self.sp = None
        self.lock = threading.Lock()
        self.init_spotify()

    def init_spotify(self):
        client_id = os.getenv(f"{self.account_prefix}_account_id")
        client_secret = os.getenv(f"{self.account_prefix}_account_secret")
        refresh_token = os.getenv(f"{self.account_prefix}_account_refresh_token")

        if not all([client_id, client_secret, refresh_token]):
            raise RuntimeError(f"Incomplete Spotify credentials for {self.account_prefix}")

        scope = "user-modify-playback-state user-read-playback-state"

        token = self.get_access_token(client_id, client_secret, refresh_token)

        auth_manager = SpotifyOAuth(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri="http://127.0.0.1:8888/callback",
            scope=scope,
            cache_path=None,
            open_browser=False
        )

    # 🔑 Manually seed the token (THIS IS THE KEY)
        auth_manager._token = {
            "access_token": token,
            "token_type": "Bearer",
            "expires_in": 3600,
            "refresh_token": refresh_token,
            "scope": scope
        }

        self.sp = Spotify(auth_manager=auth_manager)

    # Sanity check (optional but recommended)
        user = self.sp.current_user()
        print(f"🔐 Authenticated as {user['display_name']} ({self.account_prefix})")

        self.ensure_device_active()


    def get_access_token(self, client_id, client_secret, refresh_token):
        """Request a new access token using refresh_token (no browser needed)"""
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

    def ensure_device_active(self):
        devices = self.sp.devices()["devices"]
        # Try to find the desired device
        for d in devices:
            if d["name"] == self.device_name:
                self.device_id = d["id"]
                print(f"✅ Device {self.device_name} detected")
                return
        print(f"⚠️ Device {self.device_name} not detected")

    def play_url(self, url):
        with self.lock:
            try:
                self.sp.start_playback(device_id=self.device_id, context_uri=url)
            except:
                leds.blink_led("red", duration=2)

    def toggle_play(self):
        with self.lock:
            playback = self.sp.current_playback()
            if playback and playback["is_playing"]:
                self.sp.pause_playback(device_id=self.device_id)
            else:
                self.sp.start_playback(device_id=self.device_id)

    def next_track(self):
        with self.lock:
            self.sp.next_track(device_id=self.device_id)

    def previous_track(self):
        with self.lock:
            self.sp.previous_track(device_id=self.device_id)

    def restart_track(self):
        with self.lock:
            playback = self.sp.current_playback()
            if playback:
                self.sp.seek_track(0, device_id=self.device_id)

    def change_volume(self, delta):
        with self.lock:
            playback = self.sp.current_playback()
            if playback:
                vol = playback["device"]["volume_percent"] + delta
                vol = max(0, min(100, vol))
                self.sp.volume(vol, device_id=self.device_id)
