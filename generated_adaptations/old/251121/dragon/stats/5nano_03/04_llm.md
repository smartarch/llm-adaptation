Reasoning and improved adaptation strategy (high-level)
- Objective: Kill the Dragon as fast as possible while keeping the population healthy enough to sustain production and DPS.
- Key constraints and observations:
  - All Warriors should end up in the Cave to attack the Dragon as soon as possible.
  - Farmers stay in the Village to farm (producing wheat) or spawn new villagers. Spawn events are triggered by assigning villagers to special spawn groups and consuming wheat.
  - Spawn events require pairs of villagers in the spawn group and a wheat cost (10 for a Farmer spawn, 12 for a Warrior spawn).
  - To avoid delaying the main DPS, use a strategy that preserves Warriors for the Cave and uses Farmers as the primary pool to enable spawning. If we divert Warriors to spawn groups, we delay attacking power.
- Improved strategy:
  - In village phase:
    - Use only Farmers to perform spawns. This preserves all existing Warriors for the Cave and attack role.
    - Spawn Farmers first (using 2 Farmers and 10 wheat per event) to boost long-term wheat production and population growth.
    - With remaining Farmers and wheat, spawn Warriors (using 2 Farmers per event and 12 wheat per event) to increase future Warrior numbers without stealing current Warriors from the Cave.
    - After allocating spawn Farmers/Warriors, the remaining Farmers stay in Village to farm, and all Warriors go to Cave.
  - In cave phase:
    - All Warriors in Cave should be assigned to attack the Dragon.
    - Farmers in Cave should return to Village (to farm or participate in spawning next turns).
- This approach prioritizes early growth (via Farmer spawns) to accelerate wheat production, enabling more spawns in future turns while maintaining a strong early DPS foundation from Warriors in the Cave.

Python code
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
        - farm: Stay in the Village and work on the farm (Farmers not used for spawning)
        - cave: Go to the Cave (Warriors)
        - spawn farmer: For every two Farmers assigned to this group and 10 wheat, a new Farmer is spawned
        - spawn warrior: For every two Farmers assigned to this group and 12 wheat, a new Warrior is spawned
        Strategy:
        - Use only Farmers to perform spawns (preserves all Warriors for the Cave).
        - Spawn Farmers first, then, if wheat allows, spawn Warriors using remaining Farmers.
        - Remaining Farmers stay in farm group; Warriors go to cave.
        """
        if not components:
            return

        # Gather indices by role
        farmer_indices = [i for i, c in enumerate(components) if getattr(c, "role", None) == "Farmer"]
        warrior_indices = [i for i, c in enumerate(components) if getattr(c, "role", None) == "Warrior"]

        total_villagers = len(components)
        wheat = int(getattr(environment.farm, "wheat", 0))

        # Spawn Farmers first using Farmers pool
        max_possible_farmer_spawns = len(farmer_indices) // 2
        farmer_events = min(max_possible_farmer_spawns, wheat // 10)

        wheat_after_farmer = wheat - (farmer_events * 10)

        # After farmer spawns, try to spawn Warriors using remaining Farmers
        remaining_farmers_for_war_spawn = len(farmer_indices) - (farmer_events * 2)
        warrior_events = min(remaining_farmers_for_war_spawn // 2, wheat_after_farmer // 12)

        # Assign indices to spawn groups
        spawn_farmer_indices = farmer_indices[: farmer_events * 2 ] if farmer_events > 0 else []
        spawn_warrior_indices = farmer_indices[ farmer_events * 2:
                                               farmer_events * 2 + warrior_events * 2] if warrior_events > 0 else []

        for idx in spawn_farmer_indices:
            environment.assign_group(components[idx], "spawn farmer")
        for idx in spawn_warrior_indices:
            environment.assign_group(components[idx], "spawn warrior")

        assigned_set = set(spawn_farmer_indices + spawn_warrior_indices)

        # Remaining villagers: Warriors go to cave, Farmers go to farm
        for idx, comp in enumerate(components):
            if idx in assigned_set:
                continue
            if getattr(comp, "role", None) == "Warrior":
                environment.assign_group(comp, "cave")
            else:
                environment.assign_group(comp, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Divide villagers in the Cave into:
        - attack: Attack the Dragon (Warriors)
        - cave: Stay in the Cave
        - village: Go to the Village
        """
        if not components:
            return

        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```