from __future__ import annotations
import abc

# Import the base adaptation interface
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Divide villagers in the Village into:
        - farm: Stay in the Village and work on the farm
        - cave: Go to the Cave
        - spawn farmer: For every two villagers assigned to this group and 10 wheat, a new Farmer is spawned
        - spawn warrior: For every two villagers assigned to this group and 12 wheat, a new Warrior is spawned

        Strategy:
        - All Warriors move to the Cave (to be available for attack).
        - Farmers stay in Village and are used to spawn new villagers, but spawning is limited to prevent runaway growth.
        - Attempt at most one farmer-spawn event per step if wheat >= 10 and at least two farmers exist.
        - If there are at least two farmers left after farmer spawning and wheat >= 12, attempt at most one warrior-spawn event.
        - This keeps a modest attacking force while growing wheat and population gradually.
        """
        if not components:
            return

        # Indices of actors by role
        farmer_indices = [i for i, c in enumerate(components) if getattr(c, "role", None) == "Farmer"]
        warrior_indices = [i for i, c in enumerate(components) if getattr(c, "role", None) == "Warrior"]

        total_villagers = len(components)
        wheat = int(getattr(environment.farm, "wheat", 0))

        # Spawn Farmer: at most 1 event
        farmer_events = 0
        if len(farmer_indices) >= 2 and wheat >= 10:
            farmer_events = 1

        wheat_after_farmer = wheat - (farmer_events * 10)

        # Spawn Warrior: at most 1 event, using remaining farmers
        warrior_events = 0
        remaining_farmers_for_war_spawn = len(farmer_indices) - (farmer_events * 2)
        if remaining_farmers_for_war_spawn >= 2 and wheat_after_farmer >= 12:
            warrior_events = 1

        # Select indices for spawn groups
        spawn_farmer_indices = farmer_indices[: farmer_events * 2] if farmer_events > 0 else []
        spawn_warrior_indices = farmer_indices[
            farmer_events * 2 : farmer_events * 2 + warrior_events * 2
        ] if warrior_events > 0 else []

        for idx in spawn_farmer_indices:
            environment.assign_group(components[idx], "spawn farmer")
        for idx in spawn_warrior_indices:
            environment.assign_group(components[idx], "spawn warrior")

        assigned = set(spawn_farmer_indices + spawn_warrior_indices)

        # Remaining villagers: Warriors go to cave; Farmers stay in farm
        for idx, comp in enumerate(components):
            if idx in assigned:
                continue
            if getattr(comp, "role", None) == "Warrior":
                environment.assign_group(comp, "cave")
            else:
                environment.assign_group(comp, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Divide villagers in the Cave into:
        - attack: Attack the Dragon
        - cave: Stay in the Cave
        - village: Go to the Village

        Strategy:
        - Use a modest, capped attack group of Warriors to attack.
        - Return other villagers (Farmers) to the Village to farm or participate in future spawns.
        """
        if not components:
            return

        # Collect Warriors in cave
        warriors_in_cave = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Cap the number of attacking Warriors to a small, manageable number
        max_attack = min(4, len(warriors_in_cave))

        for idx, c in enumerate(components):
            if getattr(c, "role", None) == "Warrior":
                if idx < max_attack:
                    environment.assign_group(c, "attack")
                else:
                    environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "village")