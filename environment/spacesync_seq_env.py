import numpy as np
import gymnasium as gym
from gymnasium import spaces
try:
    from spacesync_env import BUDGET_AGENT, LAYOUT_AGENT, STYLE_AGENT, SpaceSyncEnv
except ImportError:  # when the repo root is on the path instead of environment/
    from environment.spacesync_env import BUDGET_AGENT, LAYOUT_AGENT, STYLE_AGENT, SpaceSyncEnv

PHASES = (BUDGET_AGENT, STYLE_AGENT, LAYOUT_AGENT)
SEQ_REWARDS = dict(
    repair_pen=0.5, #layout agent spot was illegal and had to be moved
    pace_bonus=0.5, #budget agent: after a purchase, +bonus if the rest of the items are still affordable or its -bonus
)

class SpaceSyncSeqEnv(SpaceSyncEnv):
    metadata = {"name": "spacesync_v2_seq", "render_modes": ["human", "ansi"], "is_parallelizable": True}
    phase = 0
    pick = -1
    allow_usd = 0.0
    allow_frac = 0.0
    cand = None
    valid = None

    def __init__(self, catalog, mask_items=False, standing_cap=False, cap_fracs=(0.15, 0.3, 0.5, 1.0), **kw):
        super().__init__(catalog, cap_fracs=cap_fracs, **kw)
        self.cfg = {**SEQ_REWARDS, **self.cfg}

    def _legal_map(self, w, h):
        R = self.R
        out = np.zeros((R, R), dtype=bool)
        if w > R or h > R:
            return out
        occ = self.room.copy()
        for (r, c) in self.door_cells:
            occ[r, c] = 1.0
        S = np.zeros((R + 1, R + 1))
        S[1:, 1:] = occ.cumsum(0).cumsum(1)
        nx, ny = R - w + 1, R - h + 1
        sums = S[w : w + nx, h : h + ny] - S[0:nx, h : h + ny] - S[w : w + nx, 0:ny] + S[0:nx, 0:ny]
        out[:nx, :ny] = sums < 0.5
        return out

    def _refresh(self):
        left = self.budget - self.spend
        cache = {}
        cand = np.zeros(self.K, dtype=bool)
        for k in range(self.K):
            if not self.available[k] or self.c_price[k] > left + 1e-9:
                continue
            w, h = int(self.c_w[k]), int(self.c_h[k])
            for dims in ((w, h), (h, w)):
                if dims not in cache:
                    cache[dims] = self._legal_map(*dims).any()
                if cache[dims]:
                    cand[k] = True
                    break
        self.cand = cand

    def _pn_left(self):
        left = max(self.budget - self.spend, 1e-9)
        return np.clip(self.c_price / left, 0.0, 1.0).astype(np.float32)

    def _zeros(self, n):
        return np.zeros(n, dtype=np.float32)

    def reset(self, seed=None, options=None):
        super().reset(seed=seed, options=options)
        self.phase = 0
        self.pick = -1
        self.allow_usd = 0.0
        self.allow_frac = 0.0
        self.valid = np.zeros(self.K, dtype=bool)
        self.raised = 0
        self._refresh()
        return self._observations(), {a: {} for a in self.agents}

    def step(self, actions):
        cfg, R = self.cfg, self.R
        own = {a: 0.0 for a in self.possible_agents}
        team = 0.0
        agent = PHASES[self.phase]
        act = int(actions.get(agent, 0))
        terminated = False
        truncated = False

        if self.phase == 0:
            if not self.cand.any():
                terminated = True
            else:
                self.round += 1
                left = self.budget - self.spend
                tier = int(np.clip(act, 0, self.T - 1))
                allow = float(self.cap_fracs[tier]) * left
                valid = self.cand & (self.c_price <= allow + 1e-9)
                if not valid.any():
                    self.vetoes += 1
                    allow = float(self.c_price[self.cand].min())
                    valid = self.cand & (self.c_price <= allow + 1e-9)
                self.allow_usd = allow
                self.allow_frac = float(np.clip(allow / max(left, 1e-9), 0.0, 1.0))
                self.valid = valid
                self.phase = 1

        elif self.phase == 1:
            k = int(np.clip(act, 0, self.K - 1))
            if not self.valid[k]:
                own[STYLE_AGENT] -= cfg["style_invalid_pen"]
                self.invalid_items += 1
                free = np.flatnonzero(self.valid)
                k = int(free[np.argmin((free - k) % self.K)])
            self.pick = k
            own[STYLE_AGENT] += cfg["style_w"] * float(self.c_sim[k])
            self.phase = 2

        else:
            k = self.pick
            w0, h0 = int(self.c_w[k]), int(self.c_h[k])
            rot0, cell = divmod(int(np.clip(act, 0, 2 * R * R - 1)), R * R)
            x0, y0 = divmod(cell, R)
            maps = {0: self._legal_map(w0, h0), 1: self._legal_map(h0, w0)}
            if maps[rot0][x0, y0]:
                rot, x, y = rot0, x0, y0
            else:
                self.collisions += 1
                own[LAYOUT_AGENT] -= cfg["repair_pen"]
                best = None
                for r in (0, 1):
                    for (xx, yy) in np.argwhere(maps[r]):
                        d = abs(int(xx) - x0) + abs(int(yy) - y0) + (0.5 if r != rot0 else 0.0)
                        if best is None or d < best[0]:
                            best = (d, r, int(xx), int(yy))
                _, rot, x, y = best
            w, h = (h0, w0) if rot else (w0, h0)
            price = float(self.c_price[k])
            sim = float(self.c_sim[k])

            self.room[x : x + w, y : y + h] = 1.0
            self.available[k] = False
            self.spend += price
            self.placed += 1
            self.placed_sims.append(sim)
            reach = self._reach_frac()
            own[LAYOUT_AGENT] += cfg["area_w"] * (w * h) / (R * R) - cfg["walkway_pen"] * (1.0 - reach)
            own[BUDGET_AGENT] += cfg["ok_buy_bonus"]
            team += cfg["team_place"]
            row = self.catalog.iloc[int(self.shortlist[k])]
            self.layout_log.append(
                dict(item_id=row["item_id"], name=row["name"], category=row["category"],
                     x=x, y=y, w=w, h=h, rotated=bool(rot), price_usd=price, style=row["style_tag"])
            )

            n_left = self.target_items - self.placed
            if n_left > 0:
                prices = np.sort(self.c_price[self.available])
                need = float(prices[:n_left].sum())
                own[BUDGET_AGENT] += cfg["pace_bonus"] if (self.budget - self.spend) >= need else -cfg["pace_bonus"]

            self.pick = -1
            self.valid = np.zeros(self.K, dtype=bool)
            self.phase = 0
            self._refresh()
            terminated = self.placed >= self.target_items or not self.cand.any()
            truncated = (not terminated) and self.round >= self.max_rounds

        done = terminated or truncated
        if done:
            util = float(self.room.mean())
            lo, hi = cfg["util_band"]
            if lo <= util <= hi:
                team += cfg["band_bonus"]
            if self.placed > 0:
                own[STYLE_AGENT] += cfg["style_end_w"] * float(np.mean(self.placed_sims))
                if self.spend <= self.budget:
                    own[BUDGET_AGENT] += cfg["under_budget_bonus"]
                if self._reach_frac() >= cfg["walkway_min"]:
                    own[LAYOUT_AGENT] += cfg["walkway_bonus"]

        rewards = {a: own[a] + cfg["team_w"] * team for a in self.possible_agents}
        obs = self._observations()
        terminations = {a: terminated for a in self.possible_agents}
        truncations = {a: truncated for a in self.possible_agents}
        infos = {a: {} for a in self.possible_agents}
        if done:
            m = self.episode_metrics()
            infos = {a: dict(m) for a in self.possible_agents}
            self.agents = []
        return obs, rewards, terminations, truncations, infos

    def _item_block(self):
        valid = self._zeros(self.K) if self.valid is None else self.valid.astype(np.float32)
        return np.stack(
            [valid, self.c_sim.astype(np.float32), self._pn_left(),
             (self.c_w / self.R).astype(np.float32), (self.c_h / self.R).astype(np.float32)], 1
        ).ravel()

    def _picked(self):
        if self.pick < 0:
            return self._zeros(4)
        k = self.pick
        return np.array([self.c_w[k] / self.R, self.c_h[k] / self.R, self._pn_left()[k], self.c_sim[k]], dtype=np.float32)

    def _legal_obs(self):
        R = self.R
        if self.pick < 0:
            return self._zeros(2 * R * R)
        w, h = int(self.c_w[self.pick]), int(self.c_h[self.pick])
        return np.concatenate([self._legal_map(w, h).ravel(), self._legal_map(h, w).ravel()]).astype(np.float32)

    def _need_ratio(self):
        left = self.budget - self.spend
        n_left = max(self.target_items - self.placed, 0)
        if left <= 0 or self.cand is None:
            return 1.0
        prices = np.sort(self.c_price[self.available])
        return float(np.clip(prices[:n_left].sum() / left, 0.0, 1.0))

    def _observations(self):
        s = self._scalars()
        ph = np.zeros(3, dtype=np.float32)
        ph[self.phase] = 1.0
        cand = self._zeros(self.K) if self.cand is None else self.cand.astype(np.float32)
        n_left = max(self.target_items - self.placed, 0) / self.target_items

        style_obs = np.concatenate(
            [self.user_vec.astype(np.float32), self._item_block(),
             [s["t"], s["items"], s["left"], self.allow_frac], ph]
        )
        budget_obs = np.concatenate(
            [np.stack([cand, self._pn_left()], 1).ravel(),
             [s["left"], s["spent"], s["scale"], s["t"], s["items"], s["util"], n_left, self._need_ratio()], ph]
        )
        layout_obs = np.concatenate(
            [self._grid(), self._legal_obs(), self._picked(),
             [s["t"], s["items"], s["util"], s["reach"]], ph]
        )
        obs = {STYLE_AGENT: style_obs, BUDGET_AGENT: budget_obs, LAYOUT_AGENT: layout_obs}
        return {a: np.asarray(v, dtype=np.float32) for a, v in obs.items()}

    def state(self):
        s = self._scalars()
        ph = np.zeros(3, dtype=np.float32)
        ph[self.phase] = 1.0
        cand = self._zeros(self.K) if self.cand is None else self.cand.astype(np.float32)
        st = np.concatenate(
            [self._grid(), self.user_vec.astype(np.float32), self._item_block(), cand, self._picked(),
             [s["t"], s["items"], s["left"], s["util"], s["reach"], s["scale"], self.allow_frac,
              self._need_ratio()], ph]
        )
        return np.asarray(st, dtype=np.float32)


class SingleAgentSeq(gym.Env):
    metadata = {"render_modes": []}

    def __init__(self, catalog, **env_kwargs):
        super().__init__()
        self.env = SpaceSyncSeqEnv(catalog, **env_kwargs)
        e = self.env
        self.observation_space = e.state_space
        self.action_space = spaces.MultiDiscrete([e.K, e.T, 2 * e.R * e.R])

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.env.reset(seed=seed, options=options)
        return self.env.state(), {}

    def step(self, action):
        a = np.asarray(action).astype(int).reshape(-1)
        actions = {STYLE_AGENT: int(a[0]), BUDGET_AGENT: int(a[1]), LAYOUT_AGENT: int(a[2])}
        _, rew, term, trunc, info = self.env.step(actions)
        reward = float(np.mean(list(rew.values())))
        return self.env.state(), reward, bool(any(term.values())), bool(any(trunc.values())), info.get(STYLE_AGENT, {})