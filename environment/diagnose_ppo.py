"""
Finds out WHY a trained PPO model wastes rounds. Every round it plays is sorted into:

  bought               item available, tier approves it, spot is legal
  unavailable item     it picked an item that is already bought or is a padding slot
  vetoed by tier       item was available, but the price tier it chose is too low for it
  illegal placement    item available and approved, but the spot is out of bounds / overlaps / blocks the door

Run from the environment/ folder, after training with the same room size:
    python diagnose_ppo.py --model ppo_room10 --room-size 10
    python diagnose_ppo.py --model ppo_living_room_s0                 # the 15x15 run

Use the same --room-type / --room-size / --collision-pen / --empty-pen you trained with.
"""
import argparse
import sys
import warnings
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
for p in (HERE, HERE.parent):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import numpy as np
from stable_baselines3 import PPO

from catalog import load_catalog, split_catalog
from environment.single_agent_wrapper import SingleAgentSpaceSync, unpack_action

warnings.simplefilter("ignore")

LABELS = ["bought", "unavailable item", "vetoed by tier", "illegal placement"]


def classify(env, action):
    """What will happen this round, judged from the env state BEFORE the step."""
    R = env.R
    k, tier, lay = action["style_agent"], action["budget_agent"], action["layout_agent"]
    if getattr(env, "mask_items", False) and not env.available[k] and env.available.any():
        free = np.flatnonzero(env.available)
        k = int(free[np.argmin((free - k) % env.K)])  # same swap the env makes
    if not env.available[k]:
        return "unavailable item", tier
    cap_tier = env.standing_tier if getattr(env, "standing_cap", False) else tier  # the limit the env will really use
    if env.c_price[k] > env.cap_fracs[cap_tier] * env.budget:
        return "vetoed by tier", tier
    rot, cell = divmod(lay, R * R)
    x, y = divmod(cell, R)
    w, h = int(env.c_w[k]), int(env.c_h[k])
    if rot:
        w, h = h, w
    if env._check_placement(x, y, w, h) != "ok":
        return "illegal placement", tier
    return "bought", tier


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, help="saved model name, e.g. ppo_room10 (no .zip needed)")
    ap.add_argument("--room-type", default="Living Room")
    ap.add_argument("--room-size", type=int, default=15)
    ap.add_argument("--budget", type=float, default=2000.0)
    ap.add_argument("--mask-items", action="store_true", help="use if you trained with --mask-items")
    ap.add_argument("--standing-cap", action="store_true", help="use if you trained with --standing-cap")
    ap.add_argument("--collision-pen", type=float, default=2.0)
    ap.add_argument("--empty-pen", type=float, default=0.5)
    ap.add_argument("--split-seed", type=int, default=0)
    ap.add_argument("--test-frac", type=float, default=0.2)
    ap.add_argument("--episodes", type=int, default=200)
    args = ap.parse_args()

    catalog = load_catalog(args.room_type)
    _, test_df = split_catalog(catalog, test_frac=args.test_frac, seed=args.split_seed)
    env_kwargs = dict(
        budget=args.budget,
        room_size=args.room_size,
        reward_cfg=dict(collision_pen=args.collision_pen, empty_pen=args.empty_pen),
        mask_items=args.mask_items,
        standing_cap=args.standing_cap,
    )
    w = SingleAgentSpaceSync(test_df, seed=10_000, **env_kwargs)
    model = PPO.load(args.model, device="cpu")

    for name, deterministic in (("greedy", True), ("sampled", False)):
        counts, tiers, rounds = Counter(), Counter(), 0
        for i in range(args.episodes):
            obs, _ = w.reset(seed=50_000 + i)
            done = False
            while not done:
                act, _ = model.predict(obs, deterministic=deterministic)
                label, tier = classify(w.env, unpack_action(act))
                counts[label] += 1
                tiers[tier] += 1
                rounds += 1
                obs, _, term, trunc, _ = w.step(act)
                done = term or trunc
        print(f"\n{name}: {rounds} rounds over {args.episodes} held-out episodes")
        for lab in LABELS:
            print(f"  {lab:<20}{counts[lab] / rounds:6.1%}")
        caps = ", ".join(f"tier {t} ({w.env.cap_fracs[t]:.0%}): {tiers[t] / rounds:.0%}" for t in sorted(tiers))
        print(f"  price tiers chosen: {caps}")


if __name__ == "__main__":
    main()