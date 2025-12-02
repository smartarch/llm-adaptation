from __future__ import annotations
import abc

# Import the correct base class from the given module
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Assign villagers in the Village into groups without double-assignments:
        - "farm": Farmers farming in village
        - "cave": Farmers going to Cave (via cave group, but we assign to cave directly)
        - "spawn farmer": Pairs of Farmers spawn new Farmers (consume 10 wheat)
        - "spawn warrior": Pairs of Farmers spawn new Warriors (consume 12 wheat)
        Note: All Warriors should go to the Cave (not spawned here). Farmers may spawn new villagers.
        """
        # Classify by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Current wheat available for spawning
        wheat = getattr(environment.farm, "wheat", 0)

        # Determine how many spawn pairs we can form from farmers considering wheat
        max_farm_spawns = len(farmers) // 2
        possible_spawns_by_wheat = wheat // 10
        spawn_farmers_pairs = min(max_farm_spawns, possible_spawns_by_wheat)

        # Build final assignment in one pass
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "cave")
            elif role == "Farmer":
                # Decide based on position: first 2*spawn_farmers_pairs farmers go to spawn group
                # We maintain a counter over the Farmers list to ensure exact one assignment.
                # Use a static attribute on the object to track progress (or a closure). Simpler: rely on list order.
                # We assign in order: first 2*spawn_farmers_pairs to "spawn farmer", rest to "farm".
                break

        # Second pass to finalize ambitions without duplicating: we need deterministic ordering.
        # Recompute to avoid using partial loop state. Do explicit indexing:
        for idx, c in enumerate(components):
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "cave")
            elif getattr(c, "role", None) == "Farmer":
                # Farmers are ordered as they appeared; first 2*pairs go to spawn, others to farm
                if idx < 2 * spawn_farmers_pairs:
                    environment.assign_group(c, "spawn farmer")
                else:
                    environment.assign_group(c, "farm")
            else:
                # Fallback
                environment.assign_group(c, "farm")

        # Consume wheat for spawning
        wheat_consumed = 10 * spawn_farmers_pairs
        wheat = max(0, wheat - wheat_consumed)
        # Note: We do not implement "spawn warrior" here to respect all Warriors going to the Cave.

        # No explicit return; changes are applied via environment.assign_group calls

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