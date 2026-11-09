from collections import deque
import numpy as np
from gymnasium import spaces
from pettingzoo import ParallelEnv

from catalog import STYLES

STYLE_AGENT = "style_agent"
BUDGET_AGENT = "budget_agent"
LAYOUT_AGENT = "layout_agent"

DEFAULT_REWARDS = dict(
    # style
    style_w=1.0,
    style_invalid_pen=1.0,
    
    block_pen=0.3, # vetoed an item the user could afford
    veto_bonus=0.3, # vetoed an item that would have gone over budget
    ok_buy_bonus=0.2, # bought something and stayed under budget
    overspend_flat=1.0, # flat hit as soon as spend > budget
    overspend_pen=3.0, # extra hit scaled by how far over
    
    area_w=10.0, # reward = area_w * (cells placed / room cells)
    collision_pen=2.0, # out of bounds, overlap, or door
    walkway_pen=3.0, # scaled by fraction of free floor cut off from the door
    
    team_w=0.5,
    team_place=1.0,
    empty_pen=0.5,
    util_band=(0.25, 0.45),
    band_bonus=3.0,
    walkway_min=0.95,
    walkway_bonus=2.0,
    style_end_w=2.0,
    under_budget_bonus=2.0,
)


class SpaceSyncEnv(ParallelEnv):
    metadata = {"name": "spacesync_v2", "render_modes": ["human", "ansi"], "is_parallelizable": True}
    def __init__(
        self,
        catalog,
        room_size=15,
        budget=2000.0,
        shortlist_size=8,
        target_items=5,
        max_rounds=12,
        cap_fracs=(0.1, 0.2, 0.35, 0.6),
        cell_cm=30,
        randomize_user=True,
        reward_cfg=None,
        render_mode=None,
        seed=None,
    ):
        super().__init__()
        self.render_mode = render_mode
        self.R = int(room_size)
        self.budget_base = float(budget)
        self.target_items = int(target_items)
        self.max_rounds = int(max_rounds)
        self.cap_fracs = np.asarray(cap_fracs, dtype=np.float64)
        self.T = len(self.cap_fracs)
        self.randomize_user = randomize_user
        self.cfg = {**DEFAULT_REWARDS, **(reward_cfg or {})}
        self.S = len(STYLES)
        self.rng = np.random.default_rng(seed)

        df = catalog.reset_index(drop=True)
        if len(df) < 2:
            raise ValueError("Catalog needs at least 2 items")
        self.catalog = df
        self.K = int(shortlist_size)
        max_cells = max(1, self.R // 2)  # so an item always fits in either rotation
        self._w = np.clip(np.rint(df["width_cm"].to_numpy() / cell_cm), 1, max_cells).astype(int)
        self._h = np.clip(np.rint(df["depth_cm"].to_numpy() / cell_cm), 1, max_cells).astype(int)
        self._price = df["price_usd"].to_numpy(dtype=np.float64)
        self._style = np.zeros((len(df), self.S), dtype=np.float64)
        for i, tag in enumerate(df["style_tag"]):
            self._style[i, STYLES.index(tag)] = 1.0

        # door sits at the bottom middle; the two cells in front of it stay free
        self.door = (self.R - 1, self.R // 2)
        self.door_cells = [self.door, (self.R - 2, self.R // 2)]

        self.possible_agents = [STYLE_AGENT, BUDGET_AGENT, LAYOUT_AGENT]
        self.agents = []

        self.reset(seed=seed)
        obs = self._observations()
        self._obs_spaces = {
            a: spaces.Box(-1.0, 1.0, shape=obs[a].shape, dtype=np.float32) for a in self.possible_agents
        }
        self.state_space = spaces.Box(-1.0, 1.0, shape=self.state().shape, dtype=np.float32)
        self._act_spaces = {
            STYLE_AGENT: spaces.Discrete(self.K),
            BUDGET_AGENT: spaces.Discrete(self.T),
            LAYOUT_AGENT: spaces.Discrete(2 * self.R * self.R),
        }
        self.agents = []

    def observation_space(self, agent):
        return self._obs_spaces[agent]

    def action_space(self, agent):
        return self._act_spaces[agent]

    def reset(self, seed=None, options=None):
        if seed is not None:
            self.rng = np.random.default_rng(seed)
        options = options or {}

        self.agents = list(self.possible_agents)
        self.room = np.zeros((self.R, self.R), dtype=np.float32)  # 1 = furniture

        n_real = min(self.K, len(self.catalog))
        pad = self.K - n_real
        real = self.rng.choice(len(self.catalog), size=n_real, replace=False)
        self.shortlist = np.concatenate([real, -np.ones(pad, dtype=int)])[self.rng.permutation(self.K)]
        is_real = self.shortlist >= 0
        safe = np.where(is_real, self.shortlist, 0)
        self.c_w = np.where(is_real, self._w[safe], 1)
        self.c_h = np.where(is_real, self._h[safe], 1)
        self.c_price = np.where(is_real, self._price[safe], 0.0)
        self.available = is_real.copy()

        if "user_style" in options:
            dom = int(options["user_style"])
        elif self.randomize_user:
            dom = int(self.rng.integers(self.S))
        else:
            dom = 0
        self.user_vec = np.full(self.S, 0.3 / (self.S - 1))
        self.user_vec[dom] = 0.7
        self.user_dom = dom
        if "budget" in options:
            self.budget = float(options["budget"])
        elif self.randomize_user:
            self.budget = self.budget_base * float(self.rng.uniform(0.75, 1.25))
        else:
            self.budget = self.budget_base
        sim_all = (self._style[safe] @ self.user_vec) / self.user_vec.max()
        self.c_sim = np.where(is_real, sim_all, 0.0)

        self.spend = 0.0
        self.round = 0
        self.placed = 0
        self.placed_sims = []
        self.collisions = 0
        self.empty_rounds = 0
        self.vetoes = 0
        self.invalid_items = 0
        self.layout_log = []

        return self._observations(), {a: {} for a in self.agents}

    def step(self, actions):
        cfg = self.cfg
        R = self.R
        own = {a: 0.0 for a in self.possible_agents}
        team = 0.0

        k = int(actions.get(STYLE_AGENT, 0))
        tier = int(actions.get(BUDGET_AGENT, 0))
        lay = int(actions.get(LAYOUT_AGENT, 0))
        rot, cell = divmod(lay, R * R)
        x, y = divmod(cell, R)

        self.round += 1
        purchased = False

        if not self.available[k]:
            own[STYLE_AGENT] -= cfg["style_invalid_pen"]
            self.invalid_items += 1
        else:
            price = float(self.c_price[k])
            sim = float(self.c_sim[k])
            w, h = int(self.c_w[k]), int(self.c_h[k])
            if rot:
                w, h = h, w

            own[STYLE_AGENT] += cfg["style_w"] * sim

            approved = price <= self.cap_fracs[tier] * self.budget
            affordable = self.spend + price <= self.budget
            problem = self._check_placement(x, y, w, h)

            if not approved:
                self.vetoes += 1
                own[BUDGET_AGENT] += -cfg["block_pen"] if affordable else cfg["veto_bonus"]

            if problem != "ok":
                self.collisions += 1
                own[LAYOUT_AGENT] -= cfg["collision_pen"]

            if approved and problem == "ok":
                purchased = True
                self.room[x : x + w, y : y + h] = 1.0
                self.available[k] = False
                self.spend += price
                self.placed += 1
                self.placed_sims.append(sim)
                reach = self._reach_frac()
                own[LAYOUT_AGENT] += cfg["area_w"] * (w * h) / (R * R) - cfg["walkway_pen"] * (1.0 - reach)
                if self.spend > self.budget:
                    over = (self.spend - self.budget) / self.budget
                    own[BUDGET_AGENT] -= cfg["overspend_flat"] + cfg["overspend_pen"] * over
                else:
                    own[BUDGET_AGENT] += cfg["ok_buy_bonus"]
                team += cfg["team_place"]
                row = self.catalog.iloc[int(self.shortlist[k])]
                self.layout_log.append(
                    dict(
                        item_id=row["item_id"], name=row["name"], category=row["category"],
                        x=x, y=y, w=w, h=h, rotated=bool(rot),
                        price_usd=price, style=row["style_tag"],
                    )
                )

        if not purchased:
            self.empty_rounds += 1
            team -= cfg["empty_pen"]

        terminated = self.placed >= self.target_items or not self.available.any()
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

    def _candidate_arrays(self):
        pn = np.clip(self.c_price / self.budget, 0.0, 1.0)
        return (
            self.available.astype(np.float32),
            self.c_sim.astype(np.float32),
            pn.astype(np.float32),
            (self.c_w / self.R).astype(np.float32),
            (self.c_h / self.R).astype(np.float32),
        )

    def _scalars(self):
        left = float(np.clip((self.budget - self.spend) / self.budget, -1.0, 1.0))
        return dict(
            t=self.round / self.max_rounds,
            items=min(self.placed / self.target_items, 1.0),
            left=left,
            spent=float(np.clip(self.spend / self.budget, 0.0, 1.0)),
            util=float(self.room.mean()),
            reach=self._reach_frac(),
            scale=float(np.clip(self.budget / self.budget_base, 0.0, 2.0) / 2.0),
        )

    def _grid(self):
        g = self.room.copy()
        for (r, c) in self.door_cells:
            if g[r, c] == 0:
                g[r, c] = 0.5  # door zone, visible to the layout agent
        return g.ravel()

    def _observations(self):
        avail, sim, pn, w, h = self._candidate_arrays()
        s = self._scalars()
        style_obs = np.concatenate(
            [self.user_vec.astype(np.float32), np.stack([avail, sim, pn, w, h], 1).ravel(),
             [s["t"], s["items"], s["left"]]]
        )
        budget_obs = np.concatenate(
            [np.stack([avail, pn], 1).ravel(),
             [s["left"], s["spent"], s["scale"], s["t"], s["items"], s["util"]]]
        )
        layout_obs = np.concatenate(
            [self._grid(), np.stack([avail, w, h], 1).ravel(),
             [s["t"], s["items"], s["util"], s["reach"]]]
        )
        obs = {STYLE_AGENT: style_obs, BUDGET_AGENT: budget_obs, LAYOUT_AGENT: layout_obs}
        return {a: np.asarray(v, dtype=np.float32) for a, v in obs.items()}

    def state(self):
        """Global state for MAPPO's centralized critic (and the single-agent baseline)."""
        avail, sim, pn, w, h = self._candidate_arrays()
        s = self._scalars()
        st = np.concatenate(
            [self._grid(), self.user_vec.astype(np.float32), np.stack([avail, sim, pn, w, h], 1).ravel(),
             [s["t"], s["items"], s["left"], s["util"], s["reach"], s["scale"]]]
        )
        return np.asarray(st, dtype=np.float32)

    def _check_placement(self, x, y, w, h):
        if x + w > self.R or y + h > self.R:
            return "out_of_bounds"
        if self.room[x : x + w, y : y + h].any():
            return "overlap"
        for (r, c) in self.door_cells:
            if x <= r < x + w and y <= c < y + h:
                return "door"
        return "ok"

    def _reach_frac(self):
        """Fraction of free floor cells you can walk to from the door (4-connected)."""
        free = self.room == 0
        total = int(free.sum())
        if total == 0:
            return 0.0
        seen = np.zeros_like(free, dtype=bool)
        q = deque([self.door])
        seen[self.door] = True
        count = 1
        while q:
            r, c = q.popleft()
            for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nr, nc = r + dr, c + dc
                if 0 <= nr < self.R and 0 <= nc < self.R and free[nr, nc] and not seen[nr, nc]:
                    seen[nr, nc] = True
                    count += 1
                    q.append((nr, nc))
        return count / total

    def episode_metrics(self):
        """The benchmark metrics. Every method (random, generalist, IPPO, MAPPO) is scored with these."""
        lo, hi = self.cfg["util_band"]
        util = float(self.room.mean())
        rounds = max(self.round, 1)
        return dict(
            items_placed=float(self.placed),
            utilization=util,
            util_in_band=float(lo <= util <= hi),
            collision_rate=self.collisions / rounds, # illegal placement attempts per round
            empty_round_rate=self.empty_rounds / rounds, # rounds that placed nothing
            walkway_connectivity=self._reach_frac(),
            style_similarity=float(np.mean(self.placed_sims)) if self.placed_sims else 0.0,
            spend_usd=float(self.spend),
            budget_usd=float(self.budget),
            under_budget=float(self.spend <= self.budget),
            budget_used_frac=float(self.spend / self.budget),
            rounds=float(self.round),
        )

    def get_layout(self):
        """The proposed layout: position and rotation of each placed piece."""
        return list(self.layout_log)

    def render(self):
        grid = np.full((self.R, self.R), ".", dtype="<U1")
        for i, p in enumerate(self.layout_log):
            ch = chr(ord("A") + i % 26)
            grid[p["x"] : p["x"] + p["w"], p["y"] : p["y"] + p["h"]] = ch
        for (r, c) in self.door_cells:
            if grid[r, c] == ".":
                grid[r, c] = "D"
        lines = [" ".join(row) for row in grid]
        m = self.episode_metrics()
        lines.append(
            f"util {m['utilization']:.0%} | walkway {m['walkway_connectivity']:.0%} | "
            f"spend ${m['spend_usd']:.0f} / ${m['budget_usd']:.0f} | style {m['style_similarity']:.2f}"
        )
        text = "\n".join(lines)
        if self.render_mode == "human":
            print(text)
        return text