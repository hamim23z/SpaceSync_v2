import argparse
import math
import sys
import warnings
from pathlib import Path

HERE = Path(__file__).resolve().parent
for p in (HERE, HERE.parent):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import numpy as np
import pandas as pd
import torch
from tensordict import TensorDict
from torchrl.envs import MarlGroupMapType
from torchrl.envs.libs.pettingzoo import PettingZooWrapper
from torchrl.envs.utils import ExplorationType, set_exploration_type
from benchmarl.algorithms import IppoConfig, MappoConfig
from benchmarl.environments.pettingzoo.common import PettingZooClass
from benchmarl.experiment import Experiment, ExperimentConfig
from benchmarl.models.mlp import MlpConfig
from catalog import load_catalog, split_catalog
from environment.spacesync_env import BUDGET_AGENT, LAYOUT_AGENT, STYLE_AGENT, SpaceSyncEnv
from environment.spacesync_seq_env import SpaceSyncSeqEnv
warnings.simplefilter("ignore")

AGENTS = [STYLE_AGENT, BUDGET_AGENT, LAYOUT_AGENT]
METRICS = [
    "items_placed", "utilization", "util_in_band", "collision_rate", "empty_round_rate", "veto_rate", "invalid_pick_rate", "walkway_connectivity", "style_similarity", "under_budget", "budget_used_frac"
    ]

class SpaceSyncTask(PettingZooClass):
    def __init__(self, catalog_df, env_kwargs=None, sequential=False):
        self.catalog_df = catalog_df
        self.env_kwargs = env_kwargs or {}
        self.sequential = sequential
        rounds = self.env_kwargs.get("max_rounds", 12)
        super().__init__(name="spacesync", config={"max_cycles": rounds * 3 if sequential else rounds})

    def get_env_fun(self, num_envs, continuous_actions, seed, device):
        catalog_df, env_kwargs = self.catalog_df, self.env_kwargs
        env_cls = SpaceSyncSeqEnv if self.sequential else SpaceSyncEnv

        def make():
            return PettingZooWrapper(
                env=env_cls(catalog_df, seed=seed, **env_kwargs),
                group_map=MarlGroupMapType.ONE_GROUP_PER_AGENT,
                categorical_actions=True,
                return_state=True,
                done_on_any=False,
                seed=seed,
                device=device,
            )

        return make

    #benchmarl stuff setup - just simple functions i found that can help us
    def supports_continuous_actions(self):
        return False

    def supports_discrete_actions(self):
        return True

    def has_state(self):
        return True

    def has_render(self, env):
        return False

    def max_steps(self, env):
        return self.config["max_cycles"]

    def env_name(self):
        return "spacesync"


def build_experiment(algo, train_df, timesteps, seed, env_kwargs, sequential=False):
    task = SpaceSyncTask(train_df, env_kwargs, sequential)
    algo_cfg = (MappoConfig if algo == "mappo" else IppoConfig).get_from_yaml()
    cfg = ExperimentConfig.get_from_yaml()
    frames_per_batch = 1200
    cfg.sampling_device = "cpu"
    cfg.train_device = "cpu"
    cfg.buffer_device = "cpu"
    cfg.on_policy_collected_frames_per_batch = frames_per_batch
    cfg.on_policy_n_envs_per_worker = 4
    cfg.on_policy_minibatch_size = 128
    cfg.max_n_frames = int(math.ceil(timesteps / frames_per_batch) * frames_per_batch)
    cfg.evaluation = False
    cfg.render = False
    cfg.loggers = []
    cfg.create_json = False
    cfg.checkpoint_at_end = False
    cfg.checkpoint_interval = 0

    return Experiment(
        task=task,
        algorithm_config=algo_cfg,
        model_config=MlpConfig.get_from_yaml(),
        critic_model_config=MlpConfig.get_from_yaml(),
        seed=seed,
        config=cfg,
    )


@torch.no_grad()
def pick_actions(policy, obs, deterministic=True):
    td = TensorDict(
        {a: TensorDict({"observation": torch.as_tensor(obs[a]).view(1, 1, -1)}, batch_size=[1, 1]) for a in AGENTS},
        batch_size=[1],
    )
    mode = ExplorationType.DETERMINISTIC if deterministic else ExplorationType.RANDOM
    with set_exploration_type(mode):
        out = policy(td)
    return {a: int(out[a]["action"].reshape(-1)[0]) for a in AGENTS}


def evaluate_on_heldout(experiment, test_df, n_episodes, env_kwargs, deterministic=True, seed0=50_000, sequential=False):
    policy = experiment.policy
    env = (SpaceSyncSeqEnv if sequential else SpaceSyncEnv)(test_df, seed=10_000, **env_kwargs)
    rows = []
    for i in range(n_episodes):
        obs, _ = env.reset(seed=seed0 + i)
        total, info = 0.0, {}
        while env.agents:
            obs, rew, term, trunc, info = env.step(pick_actions(policy, obs, deterministic))
            total += float(np.mean(list(rew.values())))
        m = info[STYLE_AGENT]
        row = {k: m[k] for k in METRICS}
        row["return"] = total
        rows.append(row)
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--algo", choices=["ippo", "mappo"], default="ippo")
    ap.add_argument("--room-type", default="Living Room")
    ap.add_argument("--timesteps", type=int, default=200_000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--split-seed", type=int, default=0)
    ap.add_argument("--test-frac", type=float, default=0.2)
    ap.add_argument("--eval-episodes", type=int, default=200)
    ap.add_argument("--budget", type=float, default=2000.0)
    ap.add_argument("--room-size", type=int, default=15, help="grid is room-size x room-size cells of 30 cm (try 10)")
    ap.add_argument("--mask-items", action="store_true", help="swap an alread bought item for the next item")
    ap.add_argument("--standing-cap", action="store_true", help="price limit is shared and visible to all agents")
    ap.add_argument("--sequential", action="store_true", help="turn-based game: budget, then style, then layout (return is NOT comparable with the old game)")
    ap.add_argument("--collision-pen", type=float, default=2.0)
    ap.add_argument("--empty-pen", type=float, default=0.5)
    args = ap.parse_args()

    catalog = load_catalog(args.room_type)
    train_df, test_df = split_catalog(catalog, test_frac=args.test_frac, seed=args.split_seed)
    print(f"{args.room_type}: {len(train_df)} train items, {len(test_df)} held-out items")

    env_kwargs = dict(
        budget=args.budget,
        room_size=args.room_size,
        reward_cfg=dict(collision_pen=args.collision_pen, empty_pen=args.empty_pen),
        mask_items=args.mask_items,
        standing_cap=args.standing_cap,
    )
    if args.sequential:
        print("TURN-BASED game (budget -> style -> layout)")
    experiment = build_experiment(args.algo, train_df, args.timesteps, args.seed, env_kwargs, args.sequential)
    experiment.run()

    name = args.algo.upper()
    res = {
        f"{name} greedy": evaluate_on_heldout(experiment, test_df, args.eval_episodes, env_kwargs, deterministic=True, sequential=args.sequential),
        f"{name} sampled": evaluate_on_heldout(experiment, test_df, args.eval_episodes, env_kwargs, deterministic=False, sequential=args.sequential),
    }
    print(f"\nHELD-OUT items, {args.eval_episodes} episodes, train seed {args.seed}, room {args.room_size}x{args.room_size}")
    print(pd.DataFrame({k: v.mean() for k, v in res.items()}).round(3).to_string())


if __name__ == "__main__":
    main()