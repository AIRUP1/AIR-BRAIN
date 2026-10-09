"""One-time helper: sign in to Webex and print a refresh token for the dialer.

    python -m webex_batch_dialer.get_webex_token

Your Integration's redirect URI must be exactly http://localhost:3000/callback.
Credentials are read from WEBEX_CLIENT_ID / WEBEX_CLIENT_SECRET or prompted for;
the refresh token is printed to this terminal only (nothing is written to disk).
"""

import getpass
import os
import secrets
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlencode, urlparse

import requests

REDIRECT = "http://localhost:3000/callback"
SCOPES = "spark:calls_write spark:calls_read"


def main() -> int:
    client_id = os.environ.get("WEBEX_CLIENT_ID") or input("Client ID: ").strip()
    client_secret = os.environ.get("WEBEX_CLIENT_SECRET") or getpass.getpass("Client Secret: ").strip()
    state = secrets.token_urlsafe(16)
    url = "https://webexapis.com/v1/authorize?" + urlencode({
        "client_id": client_id, "response_type": "code", "redirect_uri": REDIRECT,
        "scope": SCOPES, "state": state,
    })
    got: dict = {}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            q = parse_qs(urlparse(self.path).query)
            got.update({k: v[0] for k, v in q.items()})
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Webex sign-in complete. You can close this tab.")

        def log_message(self, *a):
            pass

    print("Opening browser to sign in. If it does not open, visit:\n", url)
    webbrowser.open(url)
    srv = HTTPServer(("localhost", 3000), Handler)
    while "code" not in got and "error" not in got:
        srv.handle_request()
    if got.get("state") != state or "code" not in got:
        print("Sign-in failed:", got.get("error_description") or got.get("error") or "state mismatch")
        return 1
    r = requests.post("https://webexapis.com/v1/access_token", data={
        "grant_type": "authorization_code", "client_id": client_id,
        "client_secret": client_secret, "code": got["code"], "redirect_uri": REDIRECT,
    }, timeout=30)
    if r.status_code != 200:
        print("Token exchange failed:", r.status_code, r.text[:300])
        return 1
    print("\nSet this on the machine that runs the dialer:\n")
    print(f'export WEBEX_CLIENT_ID="{client_id}"')
    print('export WEBEX_CLIENT_SECRET="<your secret>"')
    print(f'export WEBEX_REFRESH_TOKEN="{r.json()["refresh_token"]}"')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
