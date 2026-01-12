# spot.py
import os
import threading
import requests
import spotipy
import logging

log = logging.getLogger("Spot")

class SpotInstance:
    def __init__(self, account_prefix, device_name, default_volume=50):
        self.account_prefix = account_prefix
        self.device_name = device_name
        self.default_volume = default_volume
        self.sp = None          # ensure attribute exists
        self.device_id = None   # device will be detected later
        self.lock = threading.Lock()
        self.active = False

        try:
            self.init_spotify()
        except Exception as e:
            log.warning(f"⚠️ Failed to initialize Spotify for {self.account_prefix}: {e}")

    def init_spotify(self):
        """Initialize Spotify client using refresh token (no browser)"""
        client_id = os.getenv(f"SPOTIFY_{self.account_prefix}_CLIENT_ID")
        client_secret = os.getenv(f"SPOTIFY_{self.account_prefix}_CLIENT_SECRET")
        refresh_token = os.getenv(f"SPOTIFY_{self.account_prefix}_REFRESH_TOKEN")
        scope = "user-modify-playback-state user-read-playback-state"

        if not refresh_token or not client_id or not client_secret:
            raise RuntimeError(f"Missing credentials for {self.account_prefix}")

        token = self.get_access_token(client_id, client_secret, refresh_token)
        self.sp = spotipy.Spotify(auth=token)
        self.ensure_device_active()

    def get_access_token(self, client_id, client_secret, refresh_token):
        """Request a new access token using refresh_token"""
        url = "https://accounts.spotify.com/api/token"
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": client_id,
            "client_secret": client_secret
        }
        resp = requests.post(url, data=payload)
        if resp.status_code != 200:
            raise RuntimeError(f"Failed to get access token for {self.account_prefix}: {resp.text}")
        return resp.json()["access_token"]

    def ensure_device_active(self):
        """Detect the Raspberry Pi device for playback"""
        if self.sp is None:
            log.warning(f"Spotify client not ready for {self.account_prefix}")
            return

        devices = self.sp.devices().get("devices", [])
        for d in devices:
            if d["name"] == self.device_name:
                self.device_id = d["id"]
                log.info(f"✅ Device {self.device_name} detected for account {self.account_prefix}")
                self.active = True
                return
        log.warning(f"⚠️ Device {self.device_name} not available for account {self.account_prefix}")
        self.device_id = None
        self.active = False

    def refresh_token_if_needed(self):
        """Ensure self.sp is valid"""
        if self.sp is None:
            try:
                self.init_spotify()
            except Exception as e:
                log.warning(f"⚠️ Unable to refresh Spotify client for {self.account_prefix}: {e}")

    def play_url(self, url):
        """Play a Spotify URL on the device"""
        self.refresh_token_if_needed()

        if self.sp is None or self.device_id is None:
            log.warning(f"Spotify not ready for playback ({self.account_prefix})")
            return False

        if isinstance(url, dict) and "URL" in url:
            url = url["URL"]
        if not isinstance(url, str):
            log.warning(f"Invalid URL passed to play_url: {url}")
            return False

        with self.lock:
            try:
                if url.startswith("spotify:track:") or url.startswith("spotify:episode:"):
                    self.sp.start_playback(device_id=self.device_id, uris=[url])
                else:
                    self.sp.start_playback(device_id=self.device_id, context_uri=url)
                log.info(f"▶️ Playback started on {self.device_name} ({self.account_prefix})")
                return True
            except Exception as e:
                log.warning(f"Spotify playback error ({self.account_prefix}): {e}")
                return False

    def pause(self):
        self.refresh_token_if_needed()
        if self.sp is None or self.device_id is None:
            return
        with self.lock:
            try:
                self.sp.pause_playback(device_id=self.device_id)
            except Exception as e:
                log.warning(f"Spotify pause error ({self.account_prefix}): {e}")

    def is_playing_elsewhere(self):
        """Return True if this account is active on a different device"""
        self.refresh_token_if_needed()
        if self.sp is None:
            return False
        try:
            playback = self.sp.current_playback()
            if playback is None:
                return False
            device = playback.get("device", {})
            return device.get("id") != self.device_id and playback.get("is_playing", False)
        except Exception:
            return False

    def get_current_playback(self):
        """Return current playback info"""
        self.refresh_token_if_needed()
        if self.sp is None:
            return None
        try:
            return self.sp.current_playback()
        except Exception:
            return None
