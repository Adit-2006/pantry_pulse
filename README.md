---
title: Pantry Pulse Environment Server
emoji: 🥫
colorFrom: purple
colorTo: green
sdk: docker
pinned: false
app_port: 8000
base_path: /web
tags:
  - openenv
---

# Pantry Pulse Environment

A reinforcement learning environment that simulates 30-day household pantry management. The agent must intelligently purchase groceries, manage inventory, minimize waste from spoilage, and satisfy daily nutritional needs — all within a fixed weekly budget.

> 📖 **Read the blog post:** [Pantry Pulse: Long-Horizon Logistics & Nutrition Simulation](./Blog.md)

## Training Glimpse

<details>
<summary>🚀 Live Training Loop — first 5 episodes</summary>

```
🚀 Starting Live Training Loop (100 Episodes)...
Episode 1/100 | Reward: -11.04
Episode 2/100 | Reward:   0.00
Episode 3/100 | Reward: -10.08
Episode 4/100 | Reward:  -8.79
Episode 5/100 | Reward:   1.72
```

</details>

---

## Quick Start

The simplest way to use the Pantry Pulse environment is through the `PantryPulseEnv` class:

```python
from pantry_pulse import PantryPulseAction, PantryPulseEnv

try:
    # Create environment from Docker image
    env = PantryPulseEnv.from_docker_image("pantry_pulse-env:latest")

    # Reset to day 1
    result = env.reset()
    print(f"Day: {result.observation.day}")
    print(f"Budget remaining: ${result.observation.budget_remaining:.2f}")

    # Step through the simulation
    for day in range(30):
        action = PantryPulseAction(purchases={"rice": 2, "chicken": 1})
        result = env.step(action)
        print(f"Day {result.observation.day} → Reward: {result.reward:.2f}")
        if result.done:
            break

finally:
    # Always clean up
    env.close()
```

The `PantryPulseEnv.from_docker_image()` method handles:
- Starting the Docker container
- Waiting for the server to be ready
- Connecting to the environment
- Container cleanup when you call `close()`

---

## Building the Docker Image

Before using the environment, build the Docker image from the project root:

```bash
docker build -t pantry_pulse-env:latest -f server/Dockerfile .
```

---

## Deploying to Hugging Face Spaces

Deploy your environment to Hugging Face Spaces using the `openenv push` command:

```bash
# From the environment directory (where openenv.yaml is located)
openenv push

# Or specify options
openenv push --namespace my-org --private
```

The `openenv push` command will:
1. Validate that the directory is an OpenEnv environment (checks for `openenv.yaml`)
2. Prepare a custom build for Hugging Face Docker Spaces (enables web interface)
3. Upload to Hugging Face (prompting for login if not already authenticated)

### Prerequisites

- Authenticate with Hugging Face — the command will prompt for login if not already done.

### Options

| Flag | Short | Description |
|------|-------|-------------|
| `--directory` | `-d` | Directory containing the OpenEnv environment (defaults to current directory) |
| `--repo-id` | `-r` | Repository ID in format `username/repo-name` (defaults to `username/env-name` from `openenv.yaml`) |
| `--base-image` | `-b` | Base Docker image to use (overrides Dockerfile `FROM`) |
| `--private` | — | Deploy the space as private (default: public) |

### Examples

```bash
# Push to your personal namespace
openenv push

# Push to a specific repository
openenv push --repo-id my-org/my-env

# Push with a custom base image
openenv push --base-image ghcr.io/meta-pytorch/openenv-base:latest

# Push as a private space
openenv push --private

# Combine options
openenv push --repo-id my-org/my-env --base-image custom-base:latest --private
```

After deployment, your space will be available at:
`https://huggingface.co/spaces/<repo-id>`

The deployed space includes:

| Endpoint | Description |
|----------|-------------|
| `/web` | Interactive UI for exploring the environment |
| `/docs` | Full OpenAPI / Swagger interface |
| `/health` | Container health monitoring |
| `/ws` | Persistent WebSocket session for low-latency interactions |

---

## Environment Details

### Action

**`PantryPulseAction`** — Represents the agent's purchasing decision for a given day.

| Field | Type | Description |
|-------|------|-------------|
| `purchases` | `dict[str, int]` | Item name → quantity to purchase |

### Observation

**`PantryPulseObservation`** — The environment state returned after each step.

| Field | Type | Description |
|-------|------|-------------|
| `day` | `int` | Current simulation day (1–30) |
| `inventory` | `dict` | Current pantry stock with expiry info |
| `budget_remaining` | `float` | Budget left for the week |
| `nutrition_met` | `bool` | Whether today's nutritional needs were satisfied |
| `items_expired` | `list[str]` | Items that expired today |
| `reward` | `float` | Reward signal for this step |
| `done` | `bool` | `True` on day 30 or budget exhaustion |
| `metadata` | `dict` | Additional info (step count, waste log, etc.) |

### Reward

The reward function balances nutrition, waste minimization, and budget efficiency:

| Component | Signal |
|-----------|--------|
| Nutrition goal met | `+1.0` per day |
| Item expired (waste) | `−0.5` per item |
| Over weekly budget | `−2.0` |
| Episode completion bonus | `+5.0` |

---

## Advanced Usage

### Connecting to an Existing Server

If a Pantry Pulse server is already running, connect directly:

```python
from pantry_pulse import PantryPulseEnv

env = PantryPulseEnv(base_url="<ENV_HTTP_URL_HERE>")

result = env.reset()
result = env.step(PantryPulseAction(purchases={"eggs": 6}))
```

> **Note:** When connecting to an existing server, `env.close()` will **not** stop the server.

### Using the Context Manager

The client supports context manager usage for automatic connection management:

```python
from pantry_pulse import PantryPulseAction, PantryPulseEnv

with PantryPulseEnv(base_url="http://localhost:8000") as env:
    result = env.reset()
    for day in range(30):
        action = PantryPulseAction(purchases={"bread": 1, "milk": 1})
        result = env.step(action)
        print(f"Day {result.observation.day} → Reward: {result.reward:.2f}")
        if result.done:
            break
```

The client uses WebSocket connections for:
- **Lower latency** — no HTTP connection overhead per request
- **Persistent session** — server maintains environment state across steps
- **Efficient for episodes** — ideal for many sequential steps

### Concurrent WebSocket Sessions

The server supports multiple concurrent WebSocket connections. Enable this by modifying `server/app.py` to use factory mode:

```python
# In server/app.py — use factory mode for concurrent sessions
app = create_app(
    PantryPulseEnvironment,   # Pass class, not instance
    PantryPulseAction,
    PantryPulseObservation,
    max_concurrent_envs=4,    # Allow 4 concurrent sessions
)
```

Run multiple episodes concurrently:

```python
from pantry_pulse import PantryPulseAction, PantryPulseEnv
from concurrent.futures import ThreadPoolExecutor

def run_episode(agent_id: int):
    with PantryPulseEnv(base_url="http://localhost:8000") as env:
        result = env.reset()
        for day in range(30):
            action = PantryPulseAction(purchases={"rice": 1, "chicken": 1})
            result = env.step(action)
            if result.done:
                break
        return agent_id, result.reward

# Run 4 episodes concurrently
with ThreadPoolExecutor(max_workers=4) as executor:
    results = list(executor.map(run_episode, range(4)))
```

---

## Development & Testing

### Direct Environment Testing

Test the environment logic directly without starting the HTTP server:

```bash
# From the project root
python3 server/pantry_pulse_environment.py
```

This verifies that:
- Environment resets correctly to day 1
- Step executes purchase actions and updates inventory
- Expiration logic fires on the correct days
- Rewards are calculated correctly

### Running Locally

Run the server locally for development:

```bash
uvicorn server.app:app --reload
```

---

## Project Structure

```
pantry_pulse/
├── .dockerignore                        # Docker build exclusions
├── __init__.py                          # Module exports
├── README.md                            # This file
├── openenv.yaml                         # OpenEnv manifest
├── pyproject.toml                       # Project metadata and dependencies
├── uv.lock                              # Locked dependencies (generated)
├── client.py                            # PantryPulseEnv client
├── models.py                            # Action and Observation models
└── server/
    ├── __init__.py                      # Server module exports
    ├── pantry_pulse_environment.py      # Core environment logic
    ├── app.py                           # FastAPI app (HTTP + WebSocket)
    └── Dockerfile                       # Container image definition
```
