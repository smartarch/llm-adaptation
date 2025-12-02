from __future__ import annotations
import abc

# Import the correct base class from the given module
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Assign villagers in the Village into groups with explicit one-pass assignment:
        - "farm": Farmers farming in village
        - "cave": Farmers going to Cave (via cave group, but we assign to cave directly)
        - "spawn farmer": Pairs of Farmers spawn new Farmers (consume 10 wheat)
        - "spawn warrior": Pairs of Farmers spawn new Warriors (consume 12 wheat)
        All Warriors should go to the Cave (will be attacked later).
        """
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        wheat = getattr(environment.farm, "wheat", 0)

        # Compute possible spawns
        farm_spawns = min(len(farmers) // 2, wheat // 10)
        remaining_farmers = len(farmers) - 2 * farm_spawns
        # Wheat left after farm spawns
        wheat_left = max(0, wheat - 10 * farm_spawns)

        war_spawns = 0
        if remaining_farmers >= 2:
            war_spawns = min(remaining_farmers // 2, wheat_left // 12)
        # Final wheat deduction
        wheat_consumed = 10 * farm_spawns + 12 * war_spawns
        wheat_after = max(0, wheat - wheat_consumed)

        # Assign exactly once per component
        farmer_idx = 0  # to track order among farmers
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "cave")
            elif role == "Farmer":
                # In order: first farm_spawns pairs -> spawn farmer
                if farmer_idx < 2 * farm_spawns:
                    environment.assign_group(c, "spawn farmer")
                elif farmer_idx < 2 * farm_spawns + 2 * war_spawns:
                    environment.assign_group(c, "spawn warrior")
                else:
                    environment.assign_group(c, "farm")
                farmer_idx += 1
            else:
                # Fallback
                environment.assign_group(c, "farm")

        # Note: The environment's wheat state is external; we reflect consumption by computing wheat_after
        # but we do not modify environment.farm.wheat here because the environment API does not specify a setter.
        # The test framework typically tracks consumption via spawning actions.

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Assign villagers in the Cave into groups:
        - "attack": Warriors attack the Dragon
        - "cave": Stay in the Cave
        - "village": Go to the Village
        """
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            elif role == "Farmer":
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "cave")