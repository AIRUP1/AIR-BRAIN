"""Props API: wraps cfb_props.py + serves the 3D page.

  pip install -r requirements.txt
  export ODDS_API_KEY=...        # optional: enables /api/refresh and /api/scores
  uvicorn main:app --port 8000   # open http://localhost:8000/

Data lives in ./data (players.csv, teams.csv, games.csv, props.csv). Ships with SYNTHETIC demo data.
Swap in real player logs / team numbers / games as CSVs with the same columns.
"""
import math
import os
import threading
from pathlib import Path

import httpx
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query, Request
from pydantic import BaseModel
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

import cfb_props as cp
from vault import ALLOWED, Vault, VaultError

BASE = Path(__file__).parent
DATA = Path(os.environ.get("DATA_DIR", BASE / "data"))
vault = Vault(os.environ.get("VAULT_PATH", BASE / "data" / "vault.enc"))


def key(name):
    """Vault first (if unlocked), then environment variable."""
    return vault.get(name) or os.environ.get(name)


def odds_key():
    return key("ODDS_API_KEY")
ODDS = "https://api.the-odds-api.com/v4"
SPORT = os.environ.get("ODDS_SPORT", "americanfootball_ncaaf")
BOOKS = os.environ.get("ODDS_BOOKMAKERS", "")          # e.g. "draftkings,fanduel"; blank = all US
MARKETS = {  # The Odds API market -> cfb_props stat
    "player_pass_yds": "pass_yds", "player_pass_tds": "pass_td", "player_rush_yds": "rush_yds",
    "player_reception_yds": "rec_yds", "player_receptions": "receptions",
}

app = FastAPI(title="Props API", version="1.0.0")
_lock = threading.Lock()


def _read(name, date=False):
    f = DATA / f"{name}.csv"
    if not f.exists():
        raise HTTPException(503, f"{f.name} not found in {DATA}")
    return cp.load_csv(str(f), "date" if date else None)


def _model():
    return cp.Model(_read("players", True), _read("teams"), _read("games", True))


def _clean(df: pd.DataFrame):
    df = df.replace([np.inf, -np.inf], np.nan)
    return json_safe(df.astype(object).where(df.notna(), None).to_dict("records"))


def json_safe(x):
    if isinstance(x, list):
        return [json_safe(i) for i in x]
    if isinstance(x, dict):
        return {k: json_safe(v) for k, v in x.items()}
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.floating, float)):
        return None if math.isnan(x) or math.isinf(x) else float(x)
    return x


def _priced() -> pd.DataFrame:
    props = _read("props")
    return cp.price_props(_model(), props).sort_values("pick_prob", ascending=False)


@app.get("/api/health")
def health():
    return {"status": "ok", "odds_key": bool(odds_key()), "data_dir": str(DATA)}


@app.get("/api/props")
def props(min_prob: float = Query(0, ge=0, le=1), stat: str | None = None, team: str | None = None,
          value_only: bool = False, ok_only: bool = False, limit: int = Query(200, ge=1, le=2000)):
    df = _priced()
    df = df[df["pick_prob"] >= min_prob]
    if stat:
        df = df[df["stat"] == stat]
    if team:
        df = df[df["team"] == team]
    if value_only:
        df = df[df["flag"] == "VALUE"]
    if ok_only:
        df = df[df["confidence"] == "ok"]
    return {"count": len(df), "props": _clean(df.head(limit))}


@app.get("/api/parlay")
def parlay(legs: int = Query(3, ge=1, le=10)):
    res = cp.build_parlay(_priced(), legs)
    if not res:
        raise HTTPException(404, "No picks with enough history")
    df, prob = res
    return {"legs": _clean(df[["player", "team", "stat", "line", "pick", "pick_prob"]]), "hit_probability": prob,
            "fair_decimal_odds": cp.prob_to_decimal(prob), "note": "Legs treated as independent."}


@app.get("/api/tiers")
def tiers():
    m = _model()
    ranks = cp.defense_ranks(m.teams.reset_index())
    return {"team_record": _clean(cp.team_record_by_tier(m.games, ranks)),
            "player_avgs": _clean(cp.player_avg_by_tier(m.players, ranks))}


@app.get("/api/backtest")
def backtest():
    bt = cp.backtest(_model())
    if bt.empty:
        raise HTTPException(404, "Not enough history")
    return {"rows": len(bt), "brier": float(bt["brier"].mean()),
            "mae_by_stat": _clean(bt.groupby("stat")[["abs_err_model", "abs_err_naive"]].mean().round(3).reset_index()),
            "note": "teams.csv is season-level so the backtest leaks slightly."}


@app.get("/api/raw")
def raw():
    """Raw tables for the browser page (it reprices client-side)."""
    out = {}
    for k in ("players", "teams", "games", "props"):
        df = _read(k).copy()
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
        out[k] = [{c: ("" if v is None or (isinstance(v, float) and math.isnan(v)) else str(v)) for c, v in r.items()}
                  for r in df.to_dict("records")]
    return out


# ------------------------- The Odds API (needs ODDS_API_KEY) -------------------
def _need_key():
    if not odds_key():
        raise HTTPException(503, "No ODDS_API_KEY: unlock the vault and add it, or set the env var")


def _odds_get(client, path, **params):
    r = client.get(f"{ODDS}{path}", params={"apiKey": odds_key(), **params}, timeout=30)
    if r.status_code != 200:
        raise HTTPException(502, f"Odds API {r.status_code}: {r.text[:200]}")
    return r.json(), r.headers.get("x-requests-remaining")


@app.get("/api/scores")
def scores(days_from: int = Query(1, ge=1, le=3)):
    _need_key()
    with httpx.Client() as c:
        data, rem = _odds_get(c, f"/sports/{SPORT}/scores", daysFrom=days_from)
    return {"requests_remaining": rem, "games": data}


def parse_event_props(event: dict, team_of: dict) -> tuple[list[dict], set]:
    """Convert one Odds API event-odds payload into props.csv rows (first listed bookmaker per player/stat/line).
    team_of: lowercase player name -> team name as it appears in players.csv. Returns (rows, unmatched_players)."""
    home, away = event.get("home_team", ""), event.get("away_team", "")
    rows, seen, unmatched = [], set(), set()
    for bk in event.get("bookmakers", []):
        for mk in bk.get("markets", []):
            stat = MARKETS.get(mk["key"])
            if not stat:
                continue
            by = {}
            for o in mk.get("outcomes", []):
                if o.get("point") is None or not o.get("description"):
                    continue
                by.setdefault((o["description"], o["point"]), {})[o["name"].lower()] = o["price"]
            for (player, line), px in by.items():
                if "over" not in px or "under" not in px:
                    continue
                key = (player, stat, line)
                if key in seen:
                    continue
                team = team_of.get(player.lower())
                if team is None or team.lower() not in (home.lower(), away.lower()):
                    unmatched.add(player)
                    continue
                seen.add(key)
                is_home = team.lower() == home.lower()
                rows.append(dict(player=player, team=team, opponent=away if is_home else home, stat=stat, line=line,
                                 home=int(is_home), over_odds=px["over"], under_odds=px["under"], book=bk.get("key")))
    return rows, unmatched


@app.post("/api/refresh")
def refresh(max_events: int = Query(10, ge=1, le=40)):
    """Pull current NCAAF player props from The Odds API into data/props.csv.
    Costs credits: 1 events call is free, each event-odds call costs (#markets x #regions)."""
    _need_key()
    players = _read("players")
    team_of = {p.lower(): t for p, t in players.sort_values("date")[["player", "team"]].itertuples(index=False)}
    rows, unmatched, rem = [], set(), None
    with httpx.Client() as c:
        events, rem = _odds_get(c, f"/sports/{SPORT}/events")
        for ev in events[:max_events]:
            params = dict(regions="us", markets=",".join(MARKETS), oddsFormat="american")
            if BOOKS:
                params["bookmakers"] = BOOKS
            data, rem = _odds_get(c, f"/sports/{SPORT}/events/{ev['id']}/odds", **params)
            r, u = parse_event_props(data, team_of)
            rows += r
            unmatched |= u
    if not rows:
        raise HTTPException(404, f"No props matched players.csv. Unmatched sample: {sorted(unmatched)[:10]}")
    with _lock:
        pd.DataFrame(rows).drop(columns=["book"]).to_csv(DATA / "props.csv", index=False)
    return {"props_written": len(rows), "unmatched_players": len(unmatched), "unmatched_sample": sorted(unmatched)[:10],
            "requests_remaining": rem}



# ------------------------- encrypted key vault ---------------------------------
LOCAL = {"127.0.0.1", "::1", "localhost", "testclient"}


def _local_only(req: Request):
    if os.environ.get("VAULT_ALLOW_REMOTE") != "1" and (req.client.host if req.client else "") not in LOCAL:
        raise HTTPException(403, "Vault is localhost-only. Run the server on your own machine (or set VAULT_ALLOW_REMOTE=1 behind HTTPS).")


class Pass(BaseModel):
    passphrase: str


class KeyIn(BaseModel):
    name: str
    value: str


def _vstate():
    return {"exists": vault.exists, "unlocked": vault.unlocked, "known": ALLOWED,
            "stored": vault.masked() if vault.unlocked else {}}


@app.get("/api/vault/status")
def vault_status(req: Request):
    _local_only(req)
    return _vstate()


@app.post("/api/vault/unlock")
def vault_unlock(body: Pass, req: Request):
    _local_only(req)
    try:
        vault.unlock(body.passphrase)
    except VaultError as e:
        raise HTTPException(401, str(e))
    return _vstate()


@app.post("/api/vault/set")
def vault_set(body: KeyIn, req: Request):
    _local_only(req)
    try:
        vault.set(body.name, body.value)
    except VaultError as e:
        raise HTTPException(403 if "locked" in str(e) else 400, str(e))
    return _vstate()


@app.delete("/api/vault/key/{name}")
def vault_delete(name: str, req: Request):
    _local_only(req)
    try:
        vault.delete(name)
    except VaultError as e:
        raise HTTPException(403, str(e))
    return _vstate()


@app.post("/api/vault/lock")
def vault_lock(req: Request):
    _local_only(req)
    vault.lock()
    return _vstate()


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(BASE / "static" / "index.html")


app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")
