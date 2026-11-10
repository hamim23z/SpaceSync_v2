import warnings
import numpy as np
from catalog import load_catalog
from spacesync_env import BUDGET_AGENT, LAYOUT_AGENT, STYLE_AGENT, SpaceSyncEnv
warnings.simplefilter("ignore")

def make_env():
    env = SpaceSyncEnv(load_catalog("Living Room"), randomize_user=False, seed=0)
    env.reset(seed=0, options={"budget": 100000.0, "user_style": 0})
    return env

def act(env, k, tier, x, y, rot=0):
    R = env.R
    return {STYLE_AGENT: k, BUDGET_AGENT: tier, LAYOUT_AGENT: rot * R * R + x * R + y}

def pick(env, pred):
    for k in range(env.K):
        if pred(k):
            return k
    raise AssertionError("no candidate matches")

def test_successful_placement():
    #rewards the layout agent for placing things properly
    env = make_env()
    k = pick(env, lambda k: True)
    _, r, term, trunc, _ = env.step(act(env, k, tier=3, x=0, y=0))
    assert env.placed == 1 and not env.available[k]
    assert r[LAYOUT_AGENT] > 0 and r[STYLE_AGENT] > 0
    assert env.empty_rounds == 0

def test_out_of_bounds_is_penalized_or_places_nothing():
    #penalizes if out of bounds (based on room dimension) or places nothing
    env = make_env()
    k = pick(env, lambda k: env.c_w[k] >= 2)
    _, r, *_ = env.step(act(env, k, tier=3, x=env.R - 1, y=0))
    assert env.placed == 0 and env.collisions == 1 and env.empty_rounds == 1
    assert r[LAYOUT_AGENT] < 0

def test_overlap_penalty():
    #penalizes if any furniture items are placed incorrectly
    env = make_env()
    k1 = pick(env, lambda k: True)
    env.step(act(env, k1, tier=3, x=0, y=0))
    k2 = pick(env, lambda k: env.available[k])
    _, r, *_ = env.step(act(env, k2, tier=3, x=0, y=0))
    assert env.placed == 1 and env.collisions == 1
    assert r[LAYOUT_AGENT] < 0

def test_empty_round_penalizes_the_team():
    #if the entire round, nothing is placed, all three agents get penalized
    env = make_env()
    k = pick(env, lambda k: True)
    _, r, *_ = env.step(act(env, k, tier=3, x=env.R - 1, y=env.R - 1))
    assert r[STYLE_AGENT] != r[LAYOUT_AGENT]
    assert env.empty_rounds == 1

def test_buying_the_same_item_twice_hurts_style_only():
    #if the same item is bought twice, style hurts. however, i have to fix this function
    #because the same chair can be bought multiple times bc of the dining room table or 
    #bar stools
    env = make_env()
    k = pick(env, lambda k: True)
    env.step(act(env, k, tier=3, x=0, y=0))
    _, r, *_ = env.step(act(env, k, tier=3, x=6, y=0))
    assert env.invalid_items == 1
    assert r[STYLE_AGENT] < r[LAYOUT_AGENT]
    assert env.placed == 1

def test_overspending_hurts_budget_agent():
    #penalizes the budget agent if user goes over the budget
    env = make_env()
    k = pick(env, lambda k: True)
    env.budget = float(env.c_price[k]) * 0.5
    env.spend = 0.0
    _, r, *_ = env.step(act(env, k, tier=3, x=0, y=0))
    assert env.placed == 0
    env.budget = float(env.c_price[k]) * 0.9
    env.cap_fracs = np.array([2.0, 2.0, 2.0, 2.0])
    _, r, *_ = env.step(act(env, k, tier=3, x=0, y=0))
    assert env.placed == 1 and env.spend > env.budget
    assert r[BUDGET_AGENT] < 0

def test_final_step_returns_observations_for_everyone():
    env = make_env()
    env.target_items = 1
    k = pick(env, lambda k: True)
    obs, r, term, trunc, info = env.step(act(env, k, tier=3, x=0, y=0))
    assert env.agents == []
    assert set(obs) == set(env.possible_agents)
    assert all(term.values())
    assert "utilization" in info[STYLE_AGENT]

def test_agents_get_different_rewards():
    env = make_env()
    k = pick(env, lambda k: True)
    _, r, *_ = env.step(act(env, k, tier=3, x=0, y=0))
    assert len({round(v, 6) for v in r.values()}) == 3

def test_train_and_test_catalogs_give_same_shapes():
    from catalog import split_catalog

    train, test = split_catalog(load_catalog("Living Room"))
    a, b = SpaceSyncEnv(train, seed=0), SpaceSyncEnv(test, seed=0)
    assert len(test) < b.K
    for agent in a.possible_agents:
        assert a.observation_space(agent).shape == b.observation_space(agent).shape
        assert a.action_space(agent) == b.action_space(agent)
    assert a.state_space.shape == b.state_space.shape

def test_random_rollouts_never_crash():
    env = make_env()
    rng = np.random.default_rng(0)
    for ep in range(50):
        env.reset(seed=ep)
        while env.agents:
            env.step({a: int(rng.integers(env.action_space(a).n)) for a in env.agents})
        m = env.episode_metrics()
        assert 0.0 <= m["utilization"] <= 1.0 and 0.0 <= m["walkway_connectivity"] <= 1.0
        assert not (env.room > 1).any()  # no furniture ever stacked

if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for t in tests:
        t()
        print("ok  ", t.__name__)
    print(f"\n{len(tests)} checks passed")