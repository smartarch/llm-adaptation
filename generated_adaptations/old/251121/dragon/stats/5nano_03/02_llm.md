Reasoning and adaptation strategy (high-level)
- Objective: Kill the Dragon as fast as possible. All Warriors should head to the Cave to attack; Farmers should stay in the Village to farm (and thereby grow wheat). We also want to enable population growth by using the two spawn groups.
- Village phase strategy:
  - Assign all Warriors to the cave group (to go attack the Dragon later).
  - Assign all Farmers to the farm group (to produce wheat).
  - Use the spawn groups to generate new villagers when there is enough wheat:
    - spawn farmer: for every two villagers assigned to this group and 10 wheat, a new Farmer spawns.
    - spawn warrior: for every two villagers assigned to this group and 12 wheat, a new Warrior spawns.
  - To avoid over-commitment, spawn at most 2 events for each type (i.e., up to 4 new villagers per step), and ensure we don’t exceed the available wheat or the total number of villagers.
  - Implement this by selecting non-overlapping villagers to assign to the spawn groups (the rest keep their natural role-based group).
- Cave phase strategy:
  - Warriors go to the Dragon and attack (attack group).
  - Farmers go back to the Village (village group), since they should farm or spawn elsewhere.
  - This ensures a clean, consistent behavior aligned with the stated rules.

Python implementation
```py
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
        - farm: Stay in the Village and work on the farm (Farmers)
        - cave: Go to the Cave (Warriors)
        - spawn farmer: For every two villagers in this group and 10 wheat, spawn a new Farmer
        - spawn warrior: For every two villagers in this group and 12 wheat, spawn a new Warrior
        """
        if not components:
            return

        # Separate by role for initial defaults
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        total_villagers = len(components)
        wheat = int(getattr(environment.farm, "wheat", 0))

        # First, compute how many spawn events we can support, capped to 2 per type
        max_events = total_villagers // 2  # max number of 2-villager events we can assign in total

        # Farmer spawn events (cost 10 wheat per event)
        spawn_farmer_events = min(2, wheat // 10, max_events)

        # Wheat left after allocating farmer-spawn opportunities
        wheat_after_farmer = wheat - (spawn_farmer_events * 10)

        # Warrior spawn events (cost 12 wheat per event)
        # Also ensure we have enough villagers left to form 2-villager groups
        remaining_villagers_for_spawns = max(0, total_villagers - (spawn_farmer_events * 2))
        spawn_warrior_events = min(2, wheat_after_farmer // 12, remaining_villagers_for_spawns // 2)

        # Total villagers required for spawns
        total_spawn_villagers = (spawn_farmer_events + spawn_warrior_events) * 2
        # If somehow we over-allocated due to rounding, clamp
        if total_spawn_villagers > total_villagers:
            # Reduce warrior events first, then farmer events if needed
            excess = total_spawn_villagers - total_villagers
            reducible = min(excess // 2, spawn_warrior_events)
            spawn_warrior_events -= reducible
            excess -= reducible * 2
            if excess > 0:
                spawn_farmer_events = max(0, spawn_farmer_events - (excess // 2))

        # Now pick which villagers will be assigned to spawn groups
        # We will take the first N indices for deterministic behavior
        indices = list(range(total_villagers))
        spawn_farmer_indices = indices[: spawn_farmer_events * 2] if spawn_farmer_events > 0 else []
        spawn_warrior_indices = indices[spawn_farmer_events * 2:
                                        spawn_farmer_events * 2 + spawn_warrior_events * 2] if spawn_warrior_events > 0 else []

        # Assign groups for spawn villagers
        for i in spawn_farmer_indices:
            environment.assign_group(components[i], "spawn farmer")
        for i in spawn_warrior_indices:
            environment.assign_group(components[i], "spawn warrior")

        # Remaining villagers are assigned based on their role
        assigned_set = set(spawn_farmer_indices + spawn_warrior_indices)

        for idx, comp in enumerate(components):
            if idx in assigned_set:
                # Already assigned to a spawn group; skip
                continue
            if getattr(comp, "role", None) == "Warrior":
                environment.assign_group(comp, "cave")
            else:
                # Farmers (default) stay in Village to farm
                environment.assign_group(comp, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Divide villagers in the Cave into:
        - attack: Attack the Dragon (Warriors)
        - cave: Stay in the Cave
        - village: Go to the Village (Farmers)
        """
        if not components:
            return

        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                # Farmers should go back to the Village to farm or participate in spawning
                environment.assign_group(c, "village")
```