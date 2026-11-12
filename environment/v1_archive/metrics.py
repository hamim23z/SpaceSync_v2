import warnings
import numpy as np
import pandas as pd

from catalog import load_catalog, split_catalog
from spacesync_env import LAYOUT_AGENT, BUDGET_AGENT, STYLE_AGENT, SpaceSyncEnv

#what each metric means
METRIC_DOCS = {
    "utilization": "percent of floor covered by furniture",
    "util_in_band": "1 if utilization lands in the target band (default 25-45%)",
    "collision_rate": "illegal placement attempts",
    "empty_round_rate": "rounds that placed nothing",
    "style_similarity": "mean match between placed items and the user's favorite style (0-1)",
    "under_budget": "1 if total spend <= budget",
    "budget_used_frac": "spend / budget",
    "items_placed": "number of pieces placed",
}
REPORT_COLUMNS = list(METRIC_DOCS)


def random_policy(env):
    #the v1 baseline where every agent acts at random
    def act(_obs):
        return {a: env.action_space(a).sample() for a in env.agents}
    return act


def run_episodes(env, act_fn, n_episodes=100, seed=1000):
    rows = []
    for ep in range(n_episodes):
        obs, _ = env.reset(seed=seed + ep)
        ep_ret = {a: 0.0 for a in env.possible_agents}
        while env.agents:
            obs, rew, _, _, _ = env.step(act_fn(obs))
            for a, r in rew.items():
                ep_ret[a] += r
        row = env.episode_metrics()
        for a, r in ep_ret.items():
            row[f"return_{a}"] = r
        rows.append(row)
    return pd.DataFrame(rows)


def summarize(df, columns=None):
    cols = columns or REPORT_COLUMNS
    out = pd.DataFrame({"mean": df[cols].mean(), "std": df[cols].std()})
    return out.round(3)


if __name__ == "__main__":
    warnings.simplefilter("ignore")
    catalog = load_catalog("Living Room")
    _, test = split_catalog(catalog)
    env = SpaceSyncEnv(test, seed=0)
    df = run_episodes(env, random_policy(env), n_episodes=200)
    print("random baseline on the catalog (200 episodes)")
    print(summarize(df))
    print()
    print("mean return per agent:")
    print(df[[f"return_{a}" for a in (STYLE_AGENT, BUDGET_AGENT, LAYOUT_AGENT)]].mean().round(2))