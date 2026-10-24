"""Encrypted key vault. Keys are encrypted at rest (scrypt-derived key + Fernet/AES-128-CBC+HMAC) in one file.
The passphrase is never stored. After unlock the keys live only in server memory; the API never returns them,
only masked tails. Lock (or restart) wipes them."""
import base64
import hashlib
import json
import os
import threading
import time
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

ALLOWED = {
    "ODDS_API_KEY": "The Odds API",
    "CFBD_API_KEY": "CollegeFootballData.com",
    "SPORTSGAMEODDS_KEY": "SportsGameOdds",
    "API_FOOTBALL_KEY": "API-Football",
}
SCRYPT = dict(n=2**15, r=8, p=1, maxmem=64 * 1024 * 1024, dklen=32)


class VaultError(Exception):
    pass


class Vault:
    def __init__(self, path):
        self.path = Path(path)
        self._data = None            # None = locked
        self._fernet = None
        self._salt = None
        self._fails = 0
        self._lock = threading.Lock()

    @property
    def exists(self):
        return self.path.exists()

    @property
    def unlocked(self):
        return self._data is not None

    def _derive(self, passphrase, salt):
        k = hashlib.scrypt(passphrase.encode(), salt=salt, **SCRYPT)
        return Fernet(base64.urlsafe_b64encode(k))

    def unlock(self, passphrase):
        if len(passphrase) < 8:
            raise VaultError("Passphrase must be at least 8 characters")
        with self._lock:
            if self._fails >= 3:
                time.sleep(min(2 ** (self._fails - 2), 30))      # slow brute force
            if self.exists:
                blob = self.path.read_bytes()
                salt, token = blob[:16], blob[16:]
                f = self._derive(passphrase, salt)
                try:
                    data = json.loads(f.decrypt(token))
                except InvalidToken:
                    self._fails += 1
                    raise VaultError("Wrong passphrase")
            else:
                salt, f, data = os.urandom(16), None, {}
                f = self._derive(passphrase, salt)
            self._fails = 0
            self._salt, self._fernet, self._data = salt, f, data
            if not self.exists:
                self._save()

    def _save(self):
        tmp = self.path.with_suffix(".tmp")
        tmp.write_bytes(self._salt + self._fernet.encrypt(json.dumps(self._data).encode()))
        os.chmod(tmp, 0o600)
        tmp.replace(self.path)

    def _need(self):
        if not self.unlocked:
            raise VaultError("Vault is locked")

    def set(self, name, value):
        self._need()
        if name not in ALLOWED:
            raise VaultError(f"Unknown key name: {name}")
        value = value.strip()
        if not value:
            raise VaultError("Empty value")
        with self._lock:
            self._data[name] = value
            self._save()

    def delete(self, name):
        self._need()
        with self._lock:
            self._data.pop(name, None)
            self._save()

    def get(self, name):
        return (self._data or {}).get(name)

    def lock(self):
        with self._lock:
            self._data = self._fernet = None

    def masked(self):
        self._need()
        return {k: ("•" * 6 + v[-4:] if len(v) > 8 else "•" * 6) for k, v in self._data.items()}
