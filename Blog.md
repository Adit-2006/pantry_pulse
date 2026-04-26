# Pantry Pulse: Long-Horizon Logistics & Nutrition Simulation
### A Meta OpenEnv Hackathon Submission

---

## The Problem

Most LLM benchmarks test zero-shot reasoning or short-context Q&A. Neither tells you much about what happens when you deploy a model as an autonomous agent and leave it alone for a month.

Pantry Pulse is a 30-day survival simulation built on Meta's openenv-core framework. The agent gets a $2000 budget, a five-item grocery market, and one job: hit 160g of protein per day without going broke or letting food expire.

Three things make this genuinely hard. First, food goes bad. Chicken has the best protein density at 30g per serving, but it spoils in 3 days. The agent has to figure out how much it can consume before buying — not after. Second, only one action is allowed per day: buy, consume, or wait, not both. If the agent wants to eat on Day 2, it needs to have bought food on Day 1. Third, the arithmetic compounds across 30 separate API calls, five items, variable protein densities, and fractional servings. There's no spreadsheet. Either the math tracks or it doesn't.

---

## The Environment

Each day the agent receives its current state: day number, remaining budget, inventory (quantities, protein per serving, days to expiry), today's protein total, and cumulative waste costs.

It outputs one typed JSON action per turn:

```json
{"command": "buy", "item_name": "Chicken", "servings": 5.0}
```

The market is fixed: Eggs ($12, 6g protein, 14-day shelf life), Chicken ($60, 30g, 3 days), Greek Yogurt ($40, 15g, 7 days), Spinach ($20, 2g, 4 days), Protein Powder ($100, 25g, 60 days).

Rewards are dense. Hit the daily protein target and earn up to +1.0. Let food expire and the waste cost comes straight off the reward. Survive 30 days and a final score based on average protein and budget efficiency gets calculated.

---

## Training

We fine-tuned a 7B parameter model with an online RL loop using Unsloth, trl, and the OpenEnv FastAPI backend. The learning curve (see pantry_pulse_learning_curve.png) goes through three recognizable phases.

The untrained model was bad in a predictable way. It would buy perishable food, miss the consumption window, and take heavy waste penalties — rewards around -11.04 in early episodes.

Around Episode 15 it found something worse: doing nothing. Output `{"command": "wait"}` every single day, score a safe 0.0, avoid all pain. We're calling this "agentic cowardice." The model had found a local optimum where passivity was less costly than trying, and it stayed there.

Breaking out required one change: only update the model's weights when it earned a positive reward. That filtered out the waiting-as-strategy episodes and forced it to learn from the attempts that actually worked. By Episode 100 it had settled into a reliable loop — bulk buy non-perishables early, consume consistently, restock before running low. Not sophisticated, but it works.

---

## Why It Matters

The agentic cowardice problem isn't unique to this simulation. In real deployed systems, models that discover inaction is safe will choose it. Pantry Pulse is lightweight enough to run cheaply and fast enough to iterate on, which makes it useful for testing RL approaches aimed at preventing this kind of reward hacking without needing expensive infrastructure.

The underlying skills — planning purchases against a consumption schedule, tracking resources over time, doing multi-step arithmetic without losing the thread — are exactly what autonomous agents need in logistics, health coaching, and supply chain applications. The domain here is simplified. The capability gap is real.
