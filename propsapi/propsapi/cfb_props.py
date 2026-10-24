#!/usr/bin/env python3
"""
NCAA football player-prop model.

Projects a player's stat for an upcoming game from:
  1. Recency-weighted, opponent-adjusted player history (shrunk toward a prior)
  2. Opponent defense numbers (pass / rush yards allowed vs national average)
  3. Team offense form (recent points vs season average)
  4. Game script (team vs opponent average margin + past head-to-head results)
  5. Player's own history against this opponent (heavily shrunk)
  6. Home / away

Then converts the projection to P(over)/P(under) for a sportsbook line,
compares to book odds (if given), and can assemble a parlay.

All coefficients below are STARTING VALUES. Fit them with --backtest on real
game logs before trusting any output.

INPUT FILES (CSV)
  players.csv  date,player,team,opponent,stat,value[,home]      (one row per player-game-stat)
  teams.csv    team,off_pass_ypg,off_rush_ypg,off_ppg,def_pass_ypg,def_rush_ypg,def_ppg
               (def_* = yards/points ALLOWED per game)
  games.csv    date,team,opponent,pts_for,pts_against[,home]    (both teams' perspectives)
  props.csv    player,team,opponent,stat,line[,home,over_odds,under_odds]  (American odds)

stats supported: pass_yds pass_td rush_yds rush_td rec_yds receptions rec_td

USAGE
  python cfb_props.py --demo                       # synthetic data, proves it runs
  python cfb_props.py --players players.csv --teams teams.csv --games games.csv \
                      --props props.csv --out picks.csv --parlay 3
  python cfb_props.py --players ... --teams ... --games ... --backtest
"""
import argparse
import math
import os
import sys

import numpy as np
import pandas as pd

# ----------------------------- configuration ---------------------------------
STAT_CFG = {
    #  category used for opponent-defense ratio, kind, fallback prior mean, fallback CV
    "pass_yds":   dict(cat="pass", kind="cont",  prior=215.0, cv=0.38),
    "pass_td":    dict(cat="pass", kind="count", prior=1.6,   cv=0.70),
    "rush_yds":   dict(cat="rush", kind="cont",  prior=48.0,  cv=0.80),
    "rush_td":    dict(cat="rush", kind="count", prior=0.40,  cv=1.40),
    "rec_yds":    dict(cat="pass", kind="cont",  prior=42.0,  cv=0.90),
    "receptions": dict(cat="pass", kind="count", prior=3.6,   cv=0.70),
    "rec_td":     dict(cat="pass", kind="count", prior=0.25,  cv=1.60),
}

ALPHA = 0.70        # how strongly opponent defense ratio moves a projection
HALF_LIFE = 3.0     # games; recency weighting
SHRINK_K = 3.0      # pseudo-games of prior
FORM_EXP = 0.30     # team recent-offense form exponent
FORM_N = 3          # games in "recent form"
SCRIPT_PER_PT = {"rush": 0.0020, "pass": -0.0010}   # per point of expected margin
SCRIPT_CLIP = 0.05
H2H_WEIGHT = 0.25   # weight on past head-to-head margin vs season margins
HOME_BUMP = 0.02
PLAYER_OPP_CLIP = (0.90, 1.10)
PLAYER_OPP_K = 3.0
MIN_GAMES_CONF = 4
KELLY_FRACTION = 0.25
EDGE_FLAG = 0.04


# ----------------------------- helpers ---------------------------------------
def norm_cdf(x):
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def pois_cdf(k, lam):
    k = int(math.floor(k))
    if k < 0:
        return 0.0
    return min(1.0, sum(math.exp(-lam) * lam ** i / math.factorial(i) for i in range(k + 1)))


def american_to_prob(o):
    o = float(o)
    return (-o) / (-o + 100.0) if o < 0 else 100.0 / (o + 100.0)


def prob_to_decimal(p):
    return 1.0 / p if p > 0 else float("inf")


def load_csv(path, date_col=None):
    df = pd.read_csv(path)
    if date_col and date_col in df.columns:
        df[date_col] = pd.to_datetime(df[date_col])
    return df


class Model:
    def __init__(self, players, teams, games):
        self.players = players.copy()
        self.teams = teams.set_index("team")
        self.games = games.copy()
        self.nat = self.teams.mean(numeric_only=True)

    # --- opponent defense ratio (>1 = soft defense, <1 = tough) ---
    def def_ratio(self, opp, cat):
        col = f"def_{cat}_ypg"
        if opp in self.teams.index and col in self.teams.columns:
            return float(self.teams.loc[opp, col] / self.nat[col])
        return 1.0

    def prior(self, stat):
        cfg = STAT_CFG[stat]
        rows = self.players[self.players["stat"] == stat]
        means = rows.groupby("player")["value"].mean()
        if len(means) >= 5:
            return float(means.mean())
        return cfg["prior"]

    # --- team results helpers ---
    def _team_games(self, team, as_of):
        g = self.games[(self.games["team"] == team)]
        if as_of is not None:
            g = g[g["date"] < as_of]
        return g.sort_values("date")

    def avg_margin(self, team, as_of):
        g = self._team_games(team, as_of)
        return float((g["pts_for"] - g["pts_against"]).mean()) if len(g) else 0.0

    def h2h(self, team, opp, as_of):
        g = self._team_games(team, as_of)
        g = g[g["opponent"] == opp]
        if not len(g):
            return 0.0, 0, 0, 0
        m = (g["pts_for"] - g["pts_against"])
        return float(m.mean()), int((m > 0).sum()), int((m < 0).sum()), len(g)

    def form_factor(self, team, as_of):
        g = self._team_games(team, as_of)
        if len(g) < FORM_N + 1:
            return 1.0
        season = g["pts_for"].mean()
        recent = g["pts_for"].tail(FORM_N).mean()
        if season <= 0:
            return 1.0
        return float(np.clip((recent / season) ** FORM_EXP, 0.92, 1.08))

    # --- main projection ---
    def project(self, player, team, opp, stat, home=None, as_of=None):
        cfg = STAT_CFG[stat]
        cat = cfg["cat"]
        log = self.players[(self.players["player"] == player) & (self.players["stat"] == stat)]
        if as_of is not None:
            log = log[log["date"] < as_of]
        log = log.sort_values("date")
        n = len(log)
        prior = self.prior(stat)

        if n == 0:
            mu0, adj_vals, wmean = prior, np.array([]), prior
        else:
            # remove the strength of each past opponent's defense from the raw number
            ratios = np.array([self.def_ratio(o, cat) for o in log["opponent"]])
            adj_vals = log["value"].to_numpy(dtype=float) / np.power(ratios, ALPHA)
            ages = np.arange(n - 1, -1, -1)                    # 0 = most recent
            w = 0.5 ** (ages / HALF_LIFE)
            wmean = float(np.average(adj_vals, weights=w))
            shrink = n / (n + SHRINK_K)
            mu0 = shrink * wmean + (1 - shrink) * prior

        f_opp = self.def_ratio(opp, cat) ** ALPHA
        f_form = self.form_factor(team, as_of)

        exp_margin = self.avg_margin(team, as_of) - self.avg_margin(opp, as_of)
        h_m, h_w, h_l, h_n = self.h2h(team, opp, as_of)
        exp_margin = (1 - H2H_WEIGHT * min(h_n, 3) / 3) * exp_margin + H2H_WEIGHT * min(h_n, 3) / 3 * h_m
        f_script = 1.0 + float(np.clip(SCRIPT_PER_PT[cat] * exp_margin, -SCRIPT_CLIP, SCRIPT_CLIP))

        f_home = 1.0
        if home in (1, True):
            f_home = 1.0 + HOME_BUMP
        elif home in (0, False):
            f_home = 1.0 - HOME_BUMP

        f_player_opp = 1.0
        vs = log[log["opponent"] == opp]
        if len(vs) and wmean > 0 and n:
            vs_ratios = np.array([self.def_ratio(opp, cat)])  # same opp -> same ratio
            vs_adj = vs["value"].to_numpy(dtype=float) / np.power(vs_ratios[0], ALPHA)
            r = float(vs_adj.mean() / wmean)
            m = len(vs)
            f_player_opp = float(np.clip(1 + (r - 1) * m / (m + PLAYER_OPP_K), *PLAYER_OPP_CLIP))

        mu = max(0.0, mu0 * f_opp * f_form * f_script * f_home * f_player_opp)

        # spread of outcomes
        if cfg["kind"] == "cont":
            wgt = n / (n + SHRINK_K)
            s_emp = float(np.std(adj_vals, ddof=1)) if n >= 3 else 0.0
            s_prior = cfg["cv"] * max(mu, 1e-6)
            sigma = math.sqrt(wgt * s_emp ** 2 + (1 - wgt) * s_prior ** 2)
            sigma = max(sigma, 0.25 * max(mu, 1e-6))
        else:
            sigma = math.sqrt(mu)

        return dict(
            mu=mu, sigma=sigma, n=n, kind=cfg["kind"],
            f_opp=f_opp, f_form=f_form, f_script=f_script, f_home=f_home,
            f_player_opp=f_player_opp, exp_margin=exp_margin,
            h2h=f"{h_w}-{h_l}" if h_n else "none",
        )

    @staticmethod
    def prob_over(proj, line):
        if proj["kind"] == "cont":
            z = (line - proj["mu"]) / proj["sigma"]
            return 1.0 - norm_cdf(z)
        return 1.0 - pois_cdf(line, proj["mu"])


# ----------------------------- pricing / picks -------------------------------
def price_props(model, props):
    rows = []
    for _, r in props.iterrows():
        if r["stat"] not in STAT_CFG:
            continue
        home = r["home"] if "home" in props.columns and not pd.isna(r.get("home")) else None
        proj = model.project(r["player"], r["team"], r["opponent"], r["stat"], home)
        p_over = model.prob_over(proj, float(r["line"]))
        p_under = 1.0 - p_over
        side, p = ("OVER", p_over) if p_over >= p_under else ("UNDER", p_under)

        edge = kelly = np.nan
        if "over_odds" in props.columns and not pd.isna(r.get("over_odds")) and not pd.isna(r.get("under_odds")):
            po, pu = american_to_prob(r["over_odds"]), american_to_prob(r["under_odds"])
            fair_o = po / (po + pu)
            book_p = fair_o if side == "OVER" else 1 - fair_o
            odds = r["over_odds"] if side == "OVER" else r["under_odds"]
            dec = 1 + (100 / -float(odds) if float(odds) < 0 else float(odds) / 100)
            edge = p - book_p
            b = dec - 1
            kelly = max(0.0, (p * b - (1 - p)) / b) * KELLY_FRACTION

        rows.append(dict(
            player=r["player"], team=r["team"], opp=r["opponent"], stat=r["stat"], line=r["line"],
            projection=round(proj["mu"], 2), p_over=round(p_over, 3), pick=side, pick_prob=round(p, 3),
            edge_vs_book=None if np.isnan(edge) else round(edge, 3),
            kelly_stake_pct=None if np.isnan(kelly) else round(100 * kelly, 2),
            n_games=proj["n"], confidence="low" if proj["n"] < MIN_GAMES_CONF else "ok",
            opp_def_factor=round(proj["f_opp"], 3), form_factor=round(proj["f_form"], 3),
            script_factor=round(proj["f_script"], 3), vs_opp_factor=round(proj["f_player_opp"], 3),
            exp_margin=round(proj["exp_margin"], 1), h2h_record=proj["h2h"],
            flag="VALUE" if (not np.isnan(edge) and edge >= EDGE_FLAG and proj["n"] >= MIN_GAMES_CONF) else "",
        ))
    return pd.DataFrame(rows)


def build_parlay(picks, legs):
    pool = picks[picks["confidence"] == "ok"].sort_values("pick_prob", ascending=False)
    chosen, used_teams = [], set()
    for _, r in pool.iterrows():
        if r["team"] in used_teams:      # one leg per team to limit correlation
            continue
        chosen.append(r)
        used_teams.add(r["team"])
        if len(chosen) == legs:
            break
    if not chosen:
        return None
    prob = float(np.prod([c["pick_prob"] for c in chosen]))
    return pd.DataFrame(chosen), prob


# ----------------------------- backtest --------------------------------------
def backtest(model, min_games=4):
    out = []
    for (player, stat), log in model.players.groupby(["player", "stat"]):
        log = log.sort_values("date")
        for i in range(min_games, len(log)):
            row = log.iloc[i]
            proj = model.project(player, row["team"], row["opponent"], stat,
                                 row["home"] if "home" in log.columns and not pd.isna(row.get("home")) else None,
                                 as_of=row["date"])
            naive = float(log.iloc[:i]["value"].mean())
            line = round(naive * 2) / 2 if STAT_CFG[stat]["kind"] == "cont" else math.floor(naive) + 0.5
            p_over = model.prob_over(proj, line)
            out.append(dict(stat=stat, actual=row["value"], proj=proj["mu"], naive=naive,
                            hit_over=float(row["value"] > line), p_over=p_over))
    df = pd.DataFrame(out)
    if df.empty:
        return df
    df["abs_err_model"] = (df["actual"] - df["proj"]).abs()
    df["abs_err_naive"] = (df["actual"] - df["naive"]).abs()
    df["brier"] = (df["p_over"] - df["hit_over"]) ** 2
    return df


# ----------------------------- opponent-rank tier splits ---------------------
TIERS = [("top5", 5), ("top10", 10), ("top20", 20)]
# which defense ranking applies to which stat
STAT_RANK_COL = {"pass_yds": "def_pass_ypg", "pass_td": "def_pass_ypg",
                 "rec_yds": "def_pass_ypg", "receptions": "def_pass_ypg", "rec_td": "def_pass_ypg",
                 "rush_yds": "def_rush_ypg", "rush_td": "def_rush_ypg"}


def defense_ranks(teams):
    """Rank 1 = best defense (fewest yards/points allowed). Returns DataFrame indexed by team."""
    t = teams.set_index("team") if "team" in teams.columns else teams
    out = pd.DataFrame(index=t.index)
    for col in ("def_pass_ypg", "def_rush_ypg", "def_ppg"):
        if col in t.columns:
            out[col] = t[col].rank(method="min", ascending=True).astype(int)
    return out


def team_record_by_tier(games, ranks, rank_col="def_ppg"):
    """W-L and avg margin for each team against opponents in the top 5 / 10 / 20 defenses."""
    g = games.copy()
    g["opp_rank"] = g["opponent"].map(ranks[rank_col])
    g["win"] = (g["pts_for"] > g["pts_against"]).astype(int)
    g["margin"] = g["pts_for"] - g["pts_against"]
    rows = []
    for team, tg in g.groupby("team"):
        for name, n in TIERS:
            s = tg[tg["opp_rank"] <= n]
            rows.append(dict(team=team, tier=name, games=len(s), wins=int(s["win"].sum()),
                             losses=int(len(s) - s["win"].sum()),
                             avg_pts_for=round(s["pts_for"].mean(), 1) if len(s) else None,
                             avg_pts_against=round(s["pts_against"].mean(), 1) if len(s) else None,
                             avg_margin=round(s["margin"].mean(), 1) if len(s) else None))
    return pd.DataFrame(rows)


def player_avg_by_tier(players, ranks):
    """Average of each player's stat vs opponents ranked top 5 / 10 / 20 (in the relevant
    defense: pass defense for QB/receiving stats, rush defense for rushing stats),
    next to their overall average and the difference."""
    p = players.copy()
    p["rank_col"] = p["stat"].map(STAT_RANK_COL)
    p["opp_rank"] = [ranks.loc[o, c] if o in ranks.index else np.nan
                     for o, c in zip(p["opponent"], p["rank_col"])]
    rows = []
    for (player, stat), pg in p.groupby(["player", "stat"]):
        overall = pg["value"].mean()
        for name, n in TIERS:
            s = pg[pg["opp_rank"] <= n]
            rows.append(dict(player=player, stat=stat, tier=name, games=len(s),
                             avg_vs_tier=round(s["value"].mean(), 2) if len(s) else None,
                             overall_avg=round(overall, 2),
                             diff=round(s["value"].mean() - overall, 2) if len(s) else None))
    return pd.DataFrame(rows)


def player_team_wl_by_tier(players, games, ranks):
    """Team W-L in the games where a given player played, split by opponent tier (overall defense)."""
    gi = games.set_index(["date", "team", "opponent"])
    p = players.drop_duplicates(["player", "date", "team", "opponent"]).copy()
    p["opp_rank"] = p["opponent"].map(ranks["def_ppg"])
    p["win"] = [int(gi.loc[(d, t, o), "pts_for"] > gi.loc[(d, t, o), "pts_against"])
                if (d, t, o) in gi.index else np.nan
                for d, t, o in zip(p["date"], p["team"], p["opponent"])]
    rows = []
    for player, pg in p.groupby("player"):
        for name, n in TIERS:
            s = pg[pg["opp_rank"] <= n].dropna(subset=["win"])
            rows.append(dict(player=player, tier=name, games=len(s),
                             team_wins=int(s["win"].sum()), team_losses=int(len(s) - s["win"].sum())))
    return pd.DataFrame(rows)


# ----------------------------- demo data -------------------------------------
def make_demo(path="demo_data", seed=7):
    """SYNTHETIC data only: proves the pipeline runs. Not real teams' numbers."""
    rng = np.random.default_rng(seed)
    os.makedirs(path, exist_ok=True)
    teams = [f"T{i:02d}" for i in range(1, 13)]
    t = pd.DataFrame({
        "team": teams,
        "off_pass_ypg": rng.uniform(180, 300, 12).round(1),
        "off_rush_ypg": rng.uniform(100, 220, 12).round(1),
        "off_ppg": rng.uniform(21, 38, 12).round(1),
        "def_pass_ypg": rng.uniform(170, 290, 12).round(1),
        "def_rush_ypg": rng.uniform(90, 200, 12).round(1),
        "def_ppg": rng.uniform(18, 35, 12).round(1),
    })
    t.to_csv(f"{path}/teams.csv", index=False)
    ti = t.set_index("team")
    nat_dp, nat_dr = t["def_pass_ypg"].mean(), t["def_rush_ypg"].mean()

    players = {}
    for tm in teams:
        players[(f"{tm} QB", tm, "pass_yds")] = ti.loc[tm, "off_pass_ypg"]
        players[(f"{tm} QB", tm, "pass_td")] = ti.loc[tm, "off_ppg"] / 15
        players[(f"{tm} RB", tm, "rush_yds")] = ti.loc[tm, "off_rush_ypg"] * 0.55
        players[(f"{tm} WR1", tm, "rec_yds")] = ti.loc[tm, "off_pass_ypg"] * 0.28

    prow, grow, prop_rows = [], [], []
    start = pd.Timestamp("2026-09-05")
    for wk in range(9):
        perm = rng.permutation(teams)
        for a, b in zip(perm[0::2], perm[1::2]):
            date = start + pd.Timedelta(days=7 * wk)
            pa = max(0, rng.normal(ti.loc[a, "off_ppg"], 8)); pb = max(0, rng.normal(ti.loc[b, "off_ppg"], 8))
            grow += [dict(date=date, team=a, opponent=b, pts_for=round(pa), pts_against=round(pb), home=1),
                     dict(date=date, team=b, opponent=a, pts_for=round(pb), pts_against=round(pa), home=0)]
            for (pl, tm, st), base in players.items():
                if tm not in (a, b):
                    continue
                opp = b if tm == a else a
                cat = STAT_CFG[st]["cat"]
                ratio = (ti.loc[opp, f"def_{cat}_ypg"] / (nat_dp if cat == "pass" else nat_dr)) ** ALPHA
                kind = STAT_CFG[st]["kind"]
                if kind == "cont":
                    val = max(0, base * ratio * rng.lognormal(0, 0.25))
                    val = round(val)
                else:
                    val = rng.poisson(max(0.05, base * ratio))
                home = 1 if tm == a else 0
                if wk < 8:
                    prow.append(dict(date=date, player=pl, team=tm, opponent=opp, stat=st, value=val, home=home))
                else:
                    line = round(base * 2) / 2 if kind == "cont" else (1.5 if st == "pass_td" else 0.5)
                    prop_rows.append(dict(player=pl, team=tm, opponent=opp, stat=st, line=line,
                                          home=home, over_odds=-110, under_odds=-110))
    pd.DataFrame(prow).to_csv(f"{path}/players.csv", index=False)
    pd.DataFrame(grow).to_csv(f"{path}/games.csv", index=False)
    pd.DataFrame(prop_rows).to_csv(f"{path}/props.csv", index=False)
    return path


# ----------------------------- main ------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="NCAA football player-prop model")
    ap.add_argument("--players"); ap.add_argument("--teams"); ap.add_argument("--games")
    ap.add_argument("--props"); ap.add_argument("--out", default="picks.csv")
    ap.add_argument("--parlay", type=int, default=0, help="build an N-leg parlay from top picks")
    ap.add_argument("--backtest", action="store_true")
    ap.add_argument("--demo", action="store_true", help="run on synthetic data")
    ap.add_argument("--tiers", action="store_true",
                    help="write W-L and average stats vs top-5/10/20 defenses to tiers_*.csv")
    a = ap.parse_args()

    if a.demo:
        d = make_demo()
        a.players, a.teams, a.games, a.props = (f"{d}/players.csv", f"{d}/teams.csv",
                                                f"{d}/games.csv", f"{d}/props.csv")
        print("DEMO MODE: synthetic data, outputs are NOT real picks.\n")
        a.backtest = True
        a.tiers = True

    if not (a.players and a.teams and a.games):
        ap.error("need --players --teams --games (or --demo)")

    model = Model(load_csv(a.players, "date"), load_csv(a.teams), load_csv(a.games, "date"))

    if a.backtest:
        bt = backtest(model)
        if bt.empty:
            print("Backtest: not enough history.")
        else:
            print(f"Backtest rows: {len(bt)}")
            print(bt.groupby("stat")[["abs_err_model", "abs_err_naive"]].mean().round(2))
            print(f"Brier (model p_over vs outcome): {bt['brier'].mean():.4f}   (0.25 = coin flip)")
            print("Note: teams.csv is season-level, so opponent-defense factors leak a little in backtest.\n")

    if a.tiers:
        ranks = defense_ranks(model.teams.reset_index())
        t_rec = team_record_by_tier(model.games, ranks)
        p_avg = player_avg_by_tier(model.players, ranks)
        p_wl = player_team_wl_by_tier(model.players, model.games, ranks)
        t_rec.to_csv("tiers_team_record.csv", index=False)
        p_avg.to_csv("tiers_player_avgs.csv", index=False)
        p_wl.to_csv("tiers_player_team_wl.csv", index=False)
        print("Tier splits written: tiers_team_record.csv, tiers_player_avgs.csv, tiers_player_team_wl.csv")
        print("(player stats use pass-defense rank for passing/receiving, rush-defense rank for rushing;"
              " team W-L uses points-allowed rank)\n")
        print(p_avg[p_avg["games"] > 0].head(12).to_string(index=False))
        print()

    if a.props:
        picks = price_props(model, load_csv(a.props))
        picks = picks.sort_values("pick_prob", ascending=False)
        picks.to_csv(a.out, index=False)
        print(f"Wrote {len(picks)} priced props -> {a.out}")
        print(picks.head(10)[["player", "stat", "line", "projection", "pick", "pick_prob",
                              "edge_vs_book", "confidence"]].to_string(index=False))
        if a.parlay:
            res = build_parlay(picks, a.parlay)
            if res:
                df, prob = res
                print(f"\n{a.parlay}-leg parlay (one leg per team): model hit chance {prob:.1%}, "
                      f"fair odds {prob_to_decimal(prob):.2f}x (decimal)")
                print(df[["player", "stat", "line", "pick", "pick_prob"]].to_string(index=False))
                print("Legs are treated as independent; same-game legs are positively correlated.")


if __name__ == "__main__":
    main()
