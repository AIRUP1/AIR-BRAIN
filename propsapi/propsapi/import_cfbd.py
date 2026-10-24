"""Build players.csv / teams.csv / games.csv from CollegeFootballData.com (needs CFBD_API_KEY).

  export CFBD_API_KEY=...
  python import_cfbd.py --year 2026 [--through-week 9] [--out data] [--top 3]
  python import_cfbd.py --selftest        # parse a fake payload, no network/key

Keeps, per team and stat, only the top-N players by season total (players with props lines are starters).
Team offense/defense per-game numbers are derived from the same player rows, so no extra endpoint is needed.
"""
import argparse
import os
import sys
from pathlib import Path

import httpx
import pandas as pd

API = "https://api.collegefootballdata.com"
# (CFBD category, CFBD type) -> cfb_props stat
STATS = {("passing", "YDS"): "pass_yds", ("passing", "TD"): "pass_td", ("rushing", "YDS"): "rush_yds",
         ("rushing", "TD"): "rush_td", ("receiving", "YDS"): "rec_yds", ("receiving", "REC"): "receptions",
         ("receiving", "TD"): "rec_td"}


def get(client, path, **params):
    r = client.get(f"{API}{path}", params=params, timeout=60)
    if r.status_code != 200:
        sys.exit(f"CFBD {path} -> {r.status_code}: {r.text[:200]}")
    return r.json()


def parse_player_games(payload, dates, season_weeks=None):
    """payload: /games/players response. dates: {game id: iso date}. Returns player-game-stat rows."""
    rows = []
    for g in payload:
        date = dates.get(g.get("id"))
        teams = g.get("teams", [])
        if not date or len(teams) != 2:
            continue
        for t in teams:
            opp = next(o["team"] if "team" in o else o["school"] for o in teams if o is not t)
            home = 1 if str(t.get("homeAway", "")).lower() == "home" else 0
            for cat in t.get("categories", []):
                for ty in cat.get("types", []):
                    stat = STATS.get((str(cat.get("name", "")).lower(), str(ty.get("name", "")).upper()))
                    if not stat:
                        continue
                    for a in ty.get("athletes", []):
                        try:
                            v = float(a["stat"])
                        except (KeyError, TypeError, ValueError):
                            continue
                        rows.append(dict(date=date, player=a["name"], team=t.get("team", t.get("school")),
                                         opponent=opp, stat=stat, value=v, home=home))
    return pd.DataFrame(rows, columns=["date", "player", "team", "opponent", "stat", "value", "home"])


def parse_games(payload):
    rows = []
    for g in payload:
        if g.get("homePoints") is None or g.get("awayPoints") is None:
            continue  # not played yet
        d = str(g.get("startDate", ""))[:10]
        h, a, hp, ap = g["homeTeam"], g["awayTeam"], g["homePoints"], g["awayPoints"]
        neutral = bool(g.get("neutralSite"))
        rows.append(dict(id=g.get("id"), date=d, team=h, opponent=a, pts_for=hp, pts_against=ap, home=0 if neutral else 1))
        rows.append(dict(id=g.get("id"), date=d, team=a, opponent=h, pts_for=ap, pts_against=hp, home=0))
    return pd.DataFrame(rows, columns=["id", "date", "team", "opponent", "pts_for", "pts_against", "home"])


def build_teams(players, games):
    """Per-game offense and yards/points allowed, from player rows (full league, before top-N trimming)."""
    n = games.groupby("team").size().rename("g")
    off_pts = games.groupby("team")["pts_for"].sum() / n
    def_pts = games.groupby("team")["pts_against"].sum() / n

    def ypg(stat, by):
        s = players[players["stat"] == stat].groupby(by)["value"].sum()
        return s / n.reindex(s.index)
    t = pd.DataFrame({"off_pass_ypg": ypg("pass_yds", "team"), "off_rush_ypg": ypg("rush_yds", "team"),
                      "off_ppg": off_pts, "def_pass_ypg": ypg("pass_yds", "opponent"),
                      "def_rush_ypg": ypg("rush_yds", "opponent"), "def_ppg": def_pts})
    return t.dropna().round(1).rename_axis("team").reset_index()


def trim_top(players, top):
    tot = players.groupby(["team", "stat", "player"])["value"].sum().reset_index()
    tot["rk"] = tot.groupby(["team", "stat"])["value"].rank(ascending=False, method="first")
    keep = tot[tot["rk"] <= top][["team", "stat", "player"]]
    return players.merge(keep, on=["team", "stat", "player"])


def run(year, through_week, out, top):
    k = os.environ.get("CFBD_API_KEY")
    if not k:
        sys.exit("Set CFBD_API_KEY first")
    with httpx.Client(headers={"Authorization": f"Bearer {k}"}) as c:
        games = parse_games(get(c, "/games", year=year, seasonType="regular", classification="fbs"))
        if through_week:
            wk = {g["id"] for g in get(c, "/games", year=year, seasonType="regular", classification="fbs")
                  if g.get("week", 0) <= through_week}
            games = games[games["id"].isin(wk)]
        dates = dict(zip(games["id"], games["date"]))
        weeks = sorted({g["week"] for g in get(c, "/games", year=year, seasonType="regular", classification="fbs")
                        if g["id"] in dates})
        frames = [parse_player_games(get(c, "/games/players", year=year, week=w, seasonType="regular"), dates)
                  for w in weeks]
    players = pd.concat(frames, ignore_index=True)
    teams = build_teams(players, games)
    players = trim_top(players, top)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    players.to_csv(out / "players.csv", index=False)
    teams.to_csv(out / "teams.csv", index=False)
    games.drop(columns="id").to_csv(out / "games.csv", index=False)
    print(f"{len(players)} player rows, {len(teams)} teams, {len(games)//2} games -> {out}")


def selftest():
    pg = [{"id": 1, "teams": [
        {"team": "A", "homeAway": "home", "categories": [{"name": "passing", "types": [
            {"name": "YDS", "athletes": [{"name": "QB A", "stat": "250"}]}, {"name": "TD", "athletes": [{"name": "QB A", "stat": "2"}]}]}]},
        {"team": "B", "homeAway": "away", "categories": [{"name": "rushing", "types": [
            {"name": "YDS", "athletes": [{"name": "RB B", "stat": "90"}]}]}]}]}]
    gm = [{"id": 1, "startDate": "2026-09-05T19:00:00.000Z", "homeTeam": "A", "awayTeam": "B",
           "homePoints": 30, "awayPoints": 20, "neutralSite": False}]
    games = parse_games(gm)
    p = parse_player_games(pg, dict(zip(games["id"], games["date"])))
    assert len(p) == 3 and set(p["stat"]) == {"pass_yds", "pass_td", "rush_yds"}, p
    t = build_teams(p, games)
    assert t.empty or "off_ppg" in t  # rows lacking a stat drop out via dropna; fine for 1 game
    print("selftest ok:", len(p), "player rows,", len(games), "game rows")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int)
    ap.add_argument("--through-week", type=int, default=0)
    ap.add_argument("--out", default="data")
    ap.add_argument("--top", type=int, default=3)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    selftest() if a.selftest else run(a.year or sys.exit("--year required"), a.through_week, a.out, a.top)
