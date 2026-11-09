"""
One policy makes all three decisions at once (item, price cap, placement) and
sees the whole global state. Reward = mean of the three per-agent rewards, so it 
optimizes the same total signal the team gets.
"""
import gymnasium as gym
import numpy as np
from gymnasium import spaces

from environment.spacesync_env import BUDGET_AGENT, LAYOUT_AGENT, STYLE_AGENT, SpaceSyncEnv
class SingleAgentSpaceSync(gym.Env):
    metadata = {"render_modes": []}

    def __init__(self, catalog, **env_kwargs):
        super().__init__()
        self.env = SpaceSyncEnv(catalog, **env_kwargs)
        e = self.env
        self.observation_space = e.state_space
        self.action_space = spaces.MultiDiscrete([e.K, e.T, 2 * e.R * e.R])

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.env.reset(seed=seed, options=options)
        return self.env.state(), {}

    def step(self, action):
        a = np.asarray(action).astype(int)
        actions = {STYLE_AGENT: int(a[0]), BUDGET_AGENT: int(a[1]), LAYOUT_AGENT: int(a[2])}
        _, rew, term, trunc, info = self.env.step(actions)
        reward = float(np.mean(list(rew.values())))
        terminated = bool(any(term.values()))
        truncated = bool(any(trunc.values()))
        return self.env.state(), reward, terminated, truncated, info.get(STYLE_AGENT, {})


def unpack_action(action):
    """Turn the generalist's MultiDiscrete action into the dict SpaceSyncEnv expects."""
    a = np.asarray(action).astype(int).reshape(-1)
    return {STYLE_AGENT: int(a[0]), BUDGET_AGENT: int(a[1]), LAYOUT_AGENT: int(a[2])}