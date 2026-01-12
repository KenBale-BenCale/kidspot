import os
import time
import threading
import logging
import base64
import requests
import spotipy

log = logging.getLogger("Spot")

SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"


# -----------------------------
# Token handling (no browser)
# -----------------------------
class TokenManager:
    def __init__(self, client_id, client_secret, refresh_token):
        self.client_id = client_id
        self.client_secret = client_secret
        self.sp = None
        self.refresh_token = refresh_token
        self.access_token = None
        self.expires_at = 0
        self.lock = threading.Lock()

    def _refresh(self):
        auth = base64.b64encode(
            f"{self.client_id}:{self.client_secret}".encode()
        ).decode()

        r = requests.post(
            SPOTIFY_TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token
            },
            headers={
                "Authorization": f"Basic {auth}",
                "Content-Type": "application/x-www-form-urlencoded"
            },
            timeout=10
        )
        r.raise_for_status()

        data = r.json()
        self.access_token = data["access_token"]
        self.expires_at = time.time() + data.get("expires_in", 3600) - 30

    def get_token(self):
        with self.lock:
            if not self.access_token or time.time() >= self.expires_at:
                self._refresh()
            return self.access_token


# -----------------------------
# Helpers
# -----------------------------
def normalize_spotify_url(url):
    url = url.strip()
    if "?" in url:
        url = url.split("?", 1)[0]

    if url.startswith("spotify:"):
        return url

    if "open.spotify.com" in url:
        parts = url.replace("https://open.spotify.com/", "").split("/")
        if len(parts) >= 2:
            return f"spotify:{parts[0]}:{parts[1]}"

    raise ValueError("Not a Spotify URL")


# -----------------------------
# Single account wrapper
# -----------------------------
class _SpotifyAccount:
    def __init__(self, name, client_id, client_secret, refresh_token):
        self.name = name
        self.token_mgr = TokenManager(client_id, client_secret, refresh_token)
        self.sp = None
        self.lock = threading.Lock()
        self._connect()

    def _connect(self):
        token = self.token_mgr.get_token()
        self.sp = spotipy.Spotify(auth=token)

    def ensure_connected(self):
        try:
            self.sp.current_user()
        except:
            self._connect()

    def is_active_elsewhere(self, device_id):
        try:
            pb = self.sp.current_playback()
            if not pb:
                return False
            device = pb.get("device", {})
            return device.get("id") != device_id and pb.get("is_playing", False)
        except:
            return False


# -----------------------------
# Public API
# -----------------------------
class SpotInstance:
    """
    Multi-account Spotify controller with fallback.
    """

    def __init__(self, device_name, default_volume=50):
        self.device_name = device_name
        self.default_volume = default_volume
        self.device_id = None
        self.accounts = []
        self.lock = threading.Lock()

        self._load_accounts()
        self._detect_device()
        self.log = logging.getLogger("Spot")

    # -------------------------
    # Setup
    # -------------------------
    def _load_accounts(self):
        for label in ("BEN", "NICOLA", "KIDS"):
            cid = os.getenv(f"SPOTIFY_{label}_CLIENT_ID")
            csec = os.getenv(f"SPOTIFY_{label}_CLIENT_SECRET")
            rtk = os.getenv(f"SPOTIFY_{label}_REFRESH_TOKEN")

            if not (cid and csec and rtk):
                log.warning(f"Skipping account {label} (missing credentials)")
                continue

            acc = _SpotifyAccount(label, cid, csec, rtk)
            self.accounts.append(acc)

        if not self.accounts:
            raise RuntimeError("No valid Spotify accounts available")

    def _detect_device(self):
        for acc in self.accounts:
            try:
                devices = acc.sp.devices()["devices"]
                for d in devices:
                    if self.device_name.lower() in d["name"].lower():
                        self.device_id = d["id"]
                        log.info(f"✅ Device {d['name']} detected for account {acc.name}")
                        return
            except:
                continue

        log.warning(f"⚠️ Device {self.device_name} not available for playback")

    def _ensure_device(self):
        if not self.device_id:
            self._detect_device()

    # -------------------------
    # Playback
    # -------------------------
    def play(self, url):
        with self.lock:
            try:
            # Always re-fetch devices
                devices = self.sp.devices().get("devices", [])
                device = next(
                    (d for d in devices if d["name"] == self.device_name),
                    None
                )

                if not device:
                    self.log.warning(f"⚠️ Device {self.device_name} not available for playback")
                    return False

                device_id = device["id"]

            # 🔑 CRITICAL: rebind playback session
                self.sp.transfer_playback(
                    device_id=device_id,
                    force_play=True
                )

                time.sleep(0.3)  # allow Spotify to settle

            # Normalize URL
                if isinstance(url, dict):
                    url = url.get("url")

                if url.startswith("spotify:track:") or url.startswith("spotify:episode:"):
                    self.sp.start_playback(device_id=device_id, uris=[url])
                else:
                    self.sp.start_playback(device_id=device_id, context_uri=url)

                self.log.info(f"▶️ Playing on {self.device_name}")
                return True

            except Exception as e:
                self.log.warning(f"Spotify error: {e}")
                return False
