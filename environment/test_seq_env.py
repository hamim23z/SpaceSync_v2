import argparse
import sys
import warnings
from pathlib import Path
HERE = Path(__file__).resolve().parent
for p in (HERE, HERE.parent):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
import numpy as np
from pettingzoo.test import parallel_api_test
from catalog import load_catalog, split_catalog
from environment.manual_program import heuristic_seq_action, random_action
from spacesync_seq_env import PHASES, SingleAgentSeq, SpaceSyncSeqEnv
warnings.simplefilter("ignore")

def play(env, policy, seed):
    env.reset(seed=seed)
    info = {}
    steps = 0
    while env.agents:
        _, _, _, _, info = env.step(policy(env))
        steps += 1
    return info[PHASES[0]], steps

def report(name, ok, detail=""):
    print(f"{'OK  ' if ok else 'FAIL'} {name} {detail}")
    return ok

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--room-type", default="Living Room")
    ap.add_argument("--room-size", type=int, default=10)
    ap.add_argument("--episodes", type=int, default=300)
    args = ap.parse_args()

    train_df, test_df = split_catalog(load_catalog(args.room_type), test_frac=0.2, seed=0)
    all_ok = True

    env = SpaceSyncSeqEnv(test_df, room_size=args.room_size, seed=1)
    try:
        parallel_api_test(env, num_cycles=60)
        all_ok &= report("PettingZoo API test", True)
    except Exception as e:
        all_ok &= report("PettingZoo API test", False, repr(e))

    rng = np.random.default_rng(0)
    rand_fn = lambda e: random_action(e, rng)
    rows = [play(env, rand_fn, 50_000 + i) for i in range(args.episodes)]
    m = {k: np.mean([r[0][k] for r in rows]) for k in rows[0][0]}
    all_ok &= report("random agents: no round is wasted", m["empty_round_rate"] == 0.0, f"(empty_round_rate={m['empty_round_rate']:.3f})")
    all_ok &= report("random agents: never over budget", all(r[0]["spend_usd"] <= r[0]["budget_usd"] + 1e-6 for r in rows))
    all_ok &= report("random agents: every round buys one item",
                     all(r[0]["items_placed"] == r[0]["rounds"] for r in rows))
    print(f"random agents place {m['items_placed']:.2f} items on average; "
          f"{m['invalid_pick_rate']:.0%} of item picks and {m['collision_rate']:.0%} of spots had to be fixed")

    for mode in ("cheapest", "style"):
        pol = lambda e, mode=mode: heuristic_seq_action(e, mode)
        res = [play(env, pol, 50_000 + i) for i in range(args.episodes)]
        mm = {k: np.mean([r[0][k] for r in res]) for k in res[0][0]}
        good = (mm["empty_round_rate"] == 0 and mm["collision_rate"] == 0 and mm["invalid_pick_rate"] == 0)
        all_ok &= report(f"hand-coded rules ({mode}): nothing ever has to be fixed", good)
        print(f"     places {mm['items_placed']:.2f} items, style {mm['style_similarity']:.2f}, "
              f"utilization {mm['utilization']:.0%}, walkway {mm['walkway_connectivity']:.0%}, "
              f"spend {mm['budget_used_frac']:.0%} of budget")

    def run_with_noise(seed, noisy):
        e = SpaceSyncSeqEnv(test_df, room_size=args.room_size, seed=1)
        e.reset(seed=seed)
        r2 = np.random.default_rng(7)
        while e.agents:
            acts = heuristic_seq_action(e, "style")
            if noisy:
                on = PHASES[e.phase]
                for a in PHASES:
                    if a != on:
                        acts[a] = int(r2.integers(e.action_space(a).n))
            e.step(acts)
        return [(d["item_id"], d["x"], d["y"], d["rotated"]) for d in e.get_layout()]

    same = all(run_with_noise(60_000 + i, False) == run_with_noise(60_000 + i, True) for i in range(30))
    all_ok &= report("actions from agents that are not on turn are ignored", same)
    w = SingleAgentSeq(test_df, room_size=args.room_size)
    obs, _ = w.reset(seed=1)
    done, n = False, 0
    while not done:
        obs, r, term, trunc, info = w.step(w.action_space.sample())
        done, n = term or trunc, n + 1
    all_ok &= report("single-agent wrapper runs", obs.shape == w.observation_space.shape, f"({n} steps)")
    print("\nALL OK" if all_ok else "\nSOMETHING FAILED, send me this output")

if __name__ == "__main__":
    main()