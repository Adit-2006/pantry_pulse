import random
from uuid import uuid4
from typing import List, Optional

from openenv.core.env_server.interfaces import Environment
from openenv.core.env_server.types import State

from models import PantryPulseAction, PantryPulseObservation, PantryItem

MARKET_DATA = {
    "Chicken": {"protein": 30, "price": 60, "life": 3},
    "Greek Yogurt": {"protein": 15, "price": 40, "life": 7},
    "Eggs": {"protein": 6, "price": 12, "life": 14},
    "Spinach": {"protein": 2, "price": 20, "life": 4},
    "Protein Powder": {"protein": 25, "price": 100, "life": 60}
}

class PantryPulseEnvironment(Environment):
    SUPPORTS_CONCURRENT_SESSIONS: bool = True
    
    # Store concurrent instances to route stateless HTTP requests
    _instances = {}

    def __init__(self):
        super().__init__()
        # Track these natively rather than trying to mutate a frozen OpenEnv State object
        self.episode_id = str(uuid4())
        self.step_count = 0
        
        # Initialize default values to avoid errors if attributes are accessed before reset
        self.day = 1
        self.budget = 10000.0
        self.inventory = [] 
        self.protein_goal = 160.0 
        self.history = []
        self.waste_accumulated = 0.0

    def reset(self, seed: Optional[int] = None, episode_id: Optional[str] = None, **kwargs) -> PantryPulseObservation:
        # Accept the episode_id from the OpenEnv server so routing works!
        self.episode_id = str(episode_id) if episode_id else str(uuid4())
        self.step_count = 0
        
        self.day = 1
        self.budget = 10000.0
        self.inventory = [] 
        self.protein_goal = 160.0 
        self.history = []
        self.waste_accumulated = 0.0
        
        # Save this instance in memory for routing
        self.__class__._instances[self.episode_id] = self
        
        return self._observe("System initialized. Day 1. Goal: 160g protein/day. Budget: $10,000. Buy food to survive.")

    def step(self, action: PantryPulseAction, state: Optional[dict] = None, **kwargs) -> PantryPulseObservation:
        # Route incoming requests to the correct concurrent environment instance in memory
        if state and "episode_id" in state:
            session_id = state["episode_id"]
            if session_id in self.__class__._instances:
                return self.__class__._instances[session_id]._execute_step(action)
        
        # Fallback if no matching instance is found or no state provided
        self.__class__._instances[self.episode_id] = self
        return self._execute_step(action)

    def _execute_step(self, action: PantryPulseAction) -> PantryPulseObservation:
        # Increment our native variable instead of the frozen _state
        self.step_count += 1
        msg = f"Day {self.day} action processed."
        consumed_today = 0.0
        
        # 0. Input Validation — guard against negative/zero servings
        if action.servings is not None and action.servings < 0:
            return self._observe("Invalid action: servings must be >= 0.", 0.0, False)
        
        # 1. Action Execution
        if action.command == "buy":
            if action.item_name not in MARKET_DATA:
                msg = f"Unknown item: '{action.item_name}'. Available: {list(MARKET_DATA.keys())}"
            else:
                cost = MARKET_DATA[action.item_name]["price"] * action.servings
                if self.budget >= cost:
                    self.budget -= cost
                    self.inventory.append({
                        "name": action.item_name,
                        "qty": action.servings,
                        "prot": MARKET_DATA[action.item_name]["protein"],
                        "expiry": MARKET_DATA[action.item_name]["life"] + 1  # +1: don't age on purchase day
                    })
                    msg = f"Purchased {action.servings}x {action.item_name}."
                else:
                    msg = "Transaction failed: Budget exceeded!"

        elif action.command == "consume":
            # Consume across ALL matching inventory stacks, eating expiring food first
            remaining_to_consume = action.servings
            for item in sorted(self.inventory, key=lambda x: x["expiry"]):
                if item["name"] == action.item_name and item["qty"] > 0 and remaining_to_consume > 0:
                    amount = min(item["qty"], remaining_to_consume)
                    consumed_today += amount * item["prot"]
                    item["qty"] -= amount
                    remaining_to_consume -= amount
            actual_consumed = action.servings - remaining_to_consume
            if actual_consumed > 0:
                msg = f"Consumed {actual_consumed}x {action.item_name}."
            else:
                msg = f"Cannot consume '{action.item_name}': not found in inventory."

        # 2. Aging Logic — decrement shelf life, expire food at end of day
        self.history.append(consumed_today)
        waste_today = 0.0
        
        for item in self.inventory:
            item["expiry"] -= 1
            if item["expiry"] <= 0 and item["qty"] > 0:
                cost_wasted = item["qty"] * MARKET_DATA[item["name"]]["price"]
                waste_today += cost_wasted
                self.waste_accumulated += cost_wasted
                item["qty"] = 0 
        
        self.inventory = [i for i in self.inventory if i["qty"] > 0]

        # 3. Dense Rewards
        step_reward = 0.0
        if consumed_today >= self.protein_goal:
            step_reward += 1.0
        else:
            step_reward += (consumed_today / self.protein_goal) * 0.5 
            
        if waste_today > 0:
            step_reward -= (waste_today / 50.0)
            msg += f" WARNING: Food expired! Lost ${waste_today:.2f}."

        # 4. Progression
        self.day += 1
        done = self.day > 30

        return self._observe(msg, step_reward, done)

    def _observe(self, msg: str, reward: float = 0.0, done: bool = False):
        inv_models = [PantryItem(name=i["name"], quantity=i["qty"], 
                                 protein_per_serving=i["prot"], 
                                 days_to_expiry=i["expiry"]) for i in self.inventory]
        
        obs = PantryPulseObservation(
            day=self.day, 
            budget=round(self.budget, 2),
            inventory=inv_models, 
            protein_today=self.history[-1] if self.history else 0,
            total_waste=round(self.waste_accumulated, 2),
            message=msg, 
            reward=reward, 
            done=done,
            server_state=self.state.model_dump()
        )
        return obs

    @property
    def state(self) -> State:
        # Dynamically generate and return a fresh, compliant State object for OpenEnv
        return State(episode_id=self.episode_id, step_count=self.step_count)