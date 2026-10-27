# SpaceSync

### Benchmarking Multi-Agent Reinforcement Learning in Augmented Reality
### Hamim Choudhury and Karthikeya Reddy B, for Senior Design II (CSC59867), Professor Bandyopadhyay.

SpaceSync is a team of AI agents that plan how to furnish a room, with an augmented reality (AR) app on top. Instead of one program trying to balance everything, three specialists each handle one job and work together on the final layout. The main goal of the project is to benchmark that teamwork: does a team of specialist agents actually produce better rooms than a single agent doing it all?

## Why we built this

Moving into a new apartment or house is exciting, but furnishing it is mostly guesswork. People buy a sofa that turns out too small or a bed that turns out too big, then pay again to return it. The two questions people care about most are "Can I afford this?" and "Will it even fit?"

Tools like IKEA Kreativ and Amazon's room tools exist, but they mostly focus on one thing, either how furniture fits or how it looks. SpaceSync tries to weigh fit, style, and cost together.

## How it works

Three agents share one simulated room:

| Agent | Its job |
|---|---|
| **Layout** | Place furniture so it fits, doesn't overlap, and leaves room to walk |
| **Style** | Pick pieces that match the user's theme and taste |
| **Budget** | Keep the total cost within the user's budget |

The agents are trained with reinforcement learning (MAPPO) inside a simulated room built with PettingZoo. Each agent gets its own score, plus a shared score for how good the whole room is.

**The research question:** how does splitting the job among specialist agents affect layout quality, and what benchmarks capture the tradeoff between user preference, space, and aesthetics?

To answer it, we compare:
- a single agent that does everything,
- independent agents that don't coordinate (IPPO),
- the coordinated team of specialists (MAPPO),
- the random-placement baseline from version 1.

## The app concept

1. Choose **Scan Room** or **Enter Room Dimensions**.
2. Pick a theme (dark, light, cozy, and so on).
3. List the furniture you actually need.
4. Scroll through pieces that fit your budget, change colors, and swap in bigger or smaller sizes.
5. Sort by price or recommendation.

If the room already has furniture, a camera scan detects it (YOLOv8) and sets the starting layout. If the room is empty, you enter its size and the agents place everything from scratch.

## Inputs and outputs

**You give it:** an optional room scan, the room dimensions, style preferences, budget, and feedback on suggested layouts.

**You get back:** a proposed layout (position and rotation for each piece), a score from each agent (style, space, budget), and simple suggestions such as "move this 6 inches to the left."


## Data

- [IKEA furniture dataset](https://github.com/) (Vassiliades and Bassiliades): furniture images and sizes, organized by room type
- Kaggle IKEA pricing data: prices, merged with the sizes above
- Planned for realistic room layouts: [SSR-3DFRONT](https://huggingface.co/datasets/gradient-spaces/SSR-3DFRONT/blob/main/README.md), [3D-FRONT](https://arxiv.org/abs/2011.09127), and [Structured3D](https://arxiv.org/abs/1908.00222)

Missing prices and heights are filled with category medians, and those rows are flagged. Prices change over time, so price results are a snapshot.

## Built with

Python, PettingZoo, PyTorch, OpenCV, YOLOv8 (furniture detection), CLIP (style matching), pandas, matplotlib
