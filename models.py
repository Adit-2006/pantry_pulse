# Copyright (c) Meta Platforms, Inc. and affiliates.
from pydantic import BaseModel, Field
from typing import List, Literal, Optional
from openenv.core.env_server.types import Action, Observation

class PantryItem(BaseModel):
    """Represents a single ingredient in the inventory."""
    name: str = Field(..., description="Name of the food item")
    quantity: float = Field(..., description="Number of servings available")
    protein_per_serving: float = Field(..., description="Grams of protein per serving")
    days_to_expiry: int = Field(..., description="Days remaining until food spoils")

class PantryPulseAction(Action):
    """Action for the Pantry Pulse environment - managing resources."""
    command: Literal["buy", "consume", "wait"] = Field(..., description="The action to perform")
    item_name: Optional[str] = Field(None, description="The name of the food item")
    servings: Optional[float] = Field(1.0, ge=0, description="Number of servings")

class PantryPulseObservation(Observation):
    """Observation from the Pantry Pulse environment - current world state."""
    day: int = Field(..., description="Current day of the 30-day simulation")
    budget: float = Field(..., description="Remaining budget")
    inventory: List[PantryItem] = Field(default_factory=list, description="Current food in pantry")
    protein_today: float = Field(0.0, description="Protein consumed in the current step")
    total_waste: float = Field(0.0, description="Total cost of wasted food")
    message: str = Field("", description="Status message from the environment")
    done: bool = Field(False, description="Whether the 30-day simulation is over")
    reward: float = Field(0.0, description="The dense reward signal for this step")
    server_state: Optional[dict] = Field(None, description="Persistent state for stateless HTTP requests")