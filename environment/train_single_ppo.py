import argparse
import sys
import warnings
from pathlib import Path

HERE = Path(__file__).resolve().parent
for p in (HERE, HERE.parent):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import pandas as pd
from stable_baselines3 import PPO
from catalog import load_catalog, split_catalog
from environment.single_agent_wrapper import SingleAgentSpaceSync
from environment.spacesync_seq_env import SingleAgentSeq
warnings.simplefilter("ignore")

METRICS = [
    "items_placed", "utilization", "util_in_band", "collision_rate", "empty_round_rate", "veto_rate", "invalid_pick_rate", "walkway_connectivity", "style_similarity", "under_budget", "budget_used_frac"
    ]


def rollout(env, policy, n_episodes, seed0):
    rows, returns = [], []
    for i in range(n_episodes):
        obs, _ = env.reset(seed=seed0 + i)
        done, total, info = False, 0.0, {}
        while not done:
            obs, r, term, trunc, info = env.step(policy(obs))
            total += r
            done = term or trunc
        rows.append({k: info[k] for k in METRICS})
        returns.append(total)
    df = pd.DataFrame(rows)
    df["return"] = returns
    return df

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--room-type", default="Living Room")
    ap.add_argument("--timesteps", type=int, default=200_000)
    ap.add_argument("--seed", type=int, default=0, help="training seed")
    ap.add_argument("--split-seed", type=int, default=0, help="seed for the train/test item split")
    ap.add_argument("--test-frac", type=float, default=0.2)
    ap.add_argument("--eval-episodes", type=int, default=200)
    ap.add_argument("--budget", type=float, default=2000.0)
    ap.add_argument("--room-size", type=int, default=15, help="grid is room-size x room-size cells of 30 cm")
    ap.add_argument("--collision-pen", type=float, default=2.0, help="penalty for an illegal placement")
    ap.add_argument("--empty-pen", type=float, default=0.5, help="team penalty for a round that places nothing")
    ap.add_argument("--mask-items", action="store_true", help="swap an already bought item for the next item")
    ap.add_argument("--standing-cap", action="store_true", help="price limit is shared and visible to all agents")
    ap.add_argument("--sequential", action="store_true", help="turn-based game: budget, then style, then layout")
    ap.add_argument("--save", default=None, help="where to save the model (default: ppo_<room>_s<seed>)")
    args = ap.parse_args()

    catalog = load_catalog(args.room_type)
    train_df, test_df = split_catalog(catalog, test_frac=args.test_frac, seed=args.split_seed)
    print(f"{args.room_type}: {len(train_df)} train items, {len(test_df)} held-out items")
    print(f"room {args.room_size}x{args.room_size}")
    print(f"rewards: collision_pen={args.collision_pen}, empty_pen={args.empty_pen}")

    env_kwargs = dict(
        budget=args.budget,
        room_size=args.room_size,
        reward_cfg=dict(collision_pen=args.collision_pen, empty_pen=args.empty_pen),
        mask_items=args.mask_items,
        standing_cap=args.standing_cap,
    )
    Wrapper = SingleAgentSeq if args.sequential else SingleAgentSpaceSync
    if args.sequential:
        print("TURN-BASED game (budget -> style -> layout)")
    train_env = Wrapper(train_df, seed=args.seed, **env_kwargs)
    test_env = Wrapper(test_df, seed=10_000, **env_kwargs)
    train_eval_env = Wrapper(train_df, seed=20_000, **env_kwargs)

    model = PPO("MlpPolicy", train_env, seed=args.seed, verbose=1, device="cpu")
    model.learn(total_timesteps=args.timesteps)

    save = args.save or f"ppo_{args.room_type.replace(' ', '_').lower()}_s{args.seed}"
    model.save(save)
    print(f"saved model to {save}.zip")

    ppo_greedy = lambda obs: model.predict(obs, deterministic=True)[0]
    ppo_sampled = lambda obs: model.predict(obs, deterministic=False)[0]
    random_policy = lambda obs: test_env.action_space.sample()

    test_env.action_space.seed(123)
    seed0 = 50_000
    n = args.eval_episodes
    res = {
        "random": rollout(test_env, random_policy, n, seed0),
        "PPO greedy": rollout(test_env, ppo_greedy, n, seed0),
        "PPO sampled": rollout(test_env, ppo_sampled, n, seed0),
        "PPO greedy (train items)": rollout(train_eval_env, ppo_greedy, n, seed0),
    }

    print(f"\n{n} episodes each, train seed {args.seed}. First three columns: HELD-OUT items. Last column: TRAIN items.")
    cols = METRICS + ["return"]
    table = pd.DataFrame({name: df[cols].mean() for name, df in res.items()})
    print(table.round(3).to_string())


if __name__ == "__main__":
    main()