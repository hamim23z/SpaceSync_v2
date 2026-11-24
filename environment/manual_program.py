import argparse
import sys
import warnings
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import numpy as np
import pandas as pd
from catalog import load_catalog, split_catalog
from spacesync_env import BUDGET_AGENT, LAYOUT_AGENT, STYLE_AGENT, SpaceSyncEnv
from spacesync_seq_env import SpaceSyncSeqEnv
warnings.simplefilter("ignore")

METRICS = [
    "items_placed", "utilization", "util_in_band", "collision_rate", "empty_round_rate", "veto_rate", "invalid_pick_rate", "walkway_connectivity", "style_similarity", "under_budget", "budget_used_frac"
    ]


def heuristic_action(env, mode):
    R = env.R
    budget_left = env.budget - env.spend
    max_cap = env.cap_fracs[-1] * env.budget
    ok = env.available & (env.c_price <= budget_left) & (env.c_price <= max_cap)
    idx = np.flatnonzero(ok)
    if mode == "cheapest":
        idx = sorted(idx, key=lambda k: env.c_price[k])
    else:  # style
        idx = sorted(idx, key=lambda k: (-env.c_sim[k], env.c_price[k]))

    for k in idx:
        tier = env.T - 1 if env.standing_cap else int(np.flatnonzero(env.c_price[k] <= env.cap_fracs * env.budget)[0])
        w, h = int(env.c_w[k]), int(env.c_h[k])
        for rot in (0, 1):
            ww, hh = (h, w) if rot else (w, h)
            for x in range(R - ww + 1):
                for y in range(R - hh + 1):
                    if env._check_placement(x, y, ww, hh) == "ok":
                        return {STYLE_AGENT: int(k), BUDGET_AGENT: tier, LAYOUT_AGENT: rot * R * R + x * R + y}
    return {STYLE_AGENT: 0, BUDGET_AGENT: 0, LAYOUT_AGENT: 0}


def _rank(env, idx, mode):
    if mode == "cheapest":
        return sorted(idx, key=lambda k: env.c_price[k])
    return sorted(idx, key=lambda k: (-env.c_sim[k], env.c_price[k]))


def heuristic_seq_action(env, mode):
    R = env.R
    acts = {STYLE_AGENT: 0, BUDGET_AGENT: 0, LAYOUT_AGENT: 0}
    if env.phase == 0:
        idx = _rank(env, np.flatnonzero(env.cand), mode)
        if idx:
            left = env.budget - env.spend
            ok = np.flatnonzero(env.c_price[idx[0]] <= env.cap_fracs * left + 1e-9)
            acts[BUDGET_AGENT] = int(ok[0]) if len(ok) else env.T - 1
    elif env.phase == 1:
        idx = _rank(env, np.flatnonzero(env.valid), mode)
        if idx:
            acts[STYLE_AGENT] = int(idx[0])
    else:
        k = env.pick
        w, h = int(env.c_w[k]), int(env.c_h[k])
        for rot in (0, 1):
            spots = np.argwhere(env._legal_map(*((h, w) if rot else (w, h))))
            if len(spots):
                x, y = int(spots[0][0]), int(spots[0][1])
                acts[LAYOUT_AGENT] = rot * R * R + x * R + y
                break
    return acts

def random_action(env, rng):
    R = env.R
    return {
        STYLE_AGENT: int(rng.integers(env.K)),
        BUDGET_AGENT: int(rng.integers(env.T)),
        LAYOUT_AGENT: int(rng.integers(2 * R * R)),
    }

def run(env, policy, n_episodes, seed0):
    rows = []
    for i in range(n_episodes):
        env.reset(seed=seed0 + i)
        total, info = 0.0, {}
        while env.agents:
            _, rew, _, _, info = env.step(policy(env))
            total += float(np.mean(list(rew.values())))
        m = info[STYLE_AGENT]
        row = {k: m[k] for k in METRICS}
        row["return"] = total
        rows.append(row)
    return pd.DataFrame(rows)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--room-type", default="Living Room")
    ap.add_argument("--episodes", type=int, default=200)
    ap.add_argument("--split-seed", type=int, default=0)
    ap.add_argument("--test-frac", type=float, default=0.2)
    ap.add_argument("--budget", type=float, default=2000.0)
    ap.add_argument("--room-size", type=int, default=15)
    ap.add_argument("--mask-items", action="store_true", help="swap an already bought item for the next item")
    ap.add_argument("--standing-cap", action="store_true", help="price limit is shared and visible to all agents")
    ap.add_argument("--sequential", action="store_true", help="turn-based game: budget, then style, then layout")
    ap.add_argument("--collision-pen", type=float, default=2.0)
    ap.add_argument("--empty-pen", type=float, default=0.5)
    args = ap.parse_args()

    catalog = load_catalog(args.room_type)
    train_df, test_df = split_catalog(catalog, test_frac=args.test_frac, seed=args.split_seed)
    print(f"{args.room_type}: {len(train_df)} train items, {len(test_df)} held-out items")
    print(f"room {args.room_size}x{args.room_size}, budget {args.budget}, "
          f"collision_pen={args.collision_pen}, empty_pen={args.empty_pen}")

    kwargs = dict(
        budget=args.budget,
        room_size=args.room_size,
        reward_cfg=dict(collision_pen=args.collision_pen, empty_pen=args.empty_pen),
        mask_items=args.mask_items,
        standing_cap=args.standing_cap,
    )
    rng = np.random.default_rng(123)
    seed0 = 50_000
    cols = METRICS + ["return"]
    env_cls = SpaceSyncSeqEnv if args.sequential else SpaceSyncEnv
    act = heuristic_seq_action if args.sequential else heuristic_action
    if args.sequential:
        print("TURN-BASED game (budget -> style -> layout). 'return' is not comparable with the old game.")

    for label, df in (("HELD-OUT items", test_df), ("TRAIN items", train_df)):
        env = env_cls(df, seed=1, **kwargs)
        res = {
            "random": run(env, lambda e: random_action(e, rng), args.episodes, seed0),
            "heuristic cheapest": run(env, lambda e: act(e, "cheapest"), args.episodes, seed0),
            "heuristic style": run(env, lambda e: act(e, "style"), args.episodes, seed0),
        }
        print(f"\n{label}, {args.episodes} episodes each")
        print(pd.DataFrame({k: v[cols].mean() for k, v in res.items()}).round(3).to_string())

if __name__ == "__main__":
    main()