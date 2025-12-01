Reasoning and updated strategy

Goal:
- Improve win speed while keeping correctness guarantees (no repeated assignments, all Warriors go to Cave, etc.).

What changes:
- Use a fully dynamic spawning policy without hard caps. Instead of capping farmer/warrior spawn pairs to 2, compute the maximum possible spawn pairs given the current wheat budget and the number of eligible villagers.
- Spawn as many pairs as possible:
  - Farmer spawns require 10 wheat per pair and 2 villagers per pair.
  - Warrior spawns require 12 wheat per pair and 2 villagers per pair.
- Allocate spawns first to farmers, then to warriors using the remaining wheat and farmers. Remaining farmers stay in the village to farm.
- Warriors always assigned to the cave (to attack) in the village step, preserving the requirement that all Warriors should go to the Cave.
- This approach tends to generate more combatants earlier, reducing the number of turns needed to kill the Dragon, while still respecting the one-group-per-component constraint.

Code (Python) implementing the updated strategy

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate villagers by role
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # We will compute a single final group for each farmer to avoid any repeated assignments
        final_group_for_farmer = {}

        available_wheat = int(getattr(environment.farm, "wheat", 0))

        # Maximum farmer-spawn pairs we can do this step
        max_farm_pairs_by_wheat = available_wheat // 10 if available_wheat >= 10 else 0
        max_farm_pairs_by_count = len(farmers) // 2
        sp_farm_pairs = min(max_farm_pairs_by_wheat, max_farm_pairs_by_count)

        wheat_after_farm_spawns = max(0, available_wheat - sp_farm_pairs * 10)

        # Maximum warrior-spawn pairs we can do this step
        max_war_pairs_by_wheat = wheat_after_farm_spawns // 12 if wheat_after_farm_spawns >= 12 else 0
        remaining_farmers_for_war_spawn = len(farmers) - (sp_farm_pairs * 2)
        max_war_pairs_by_count = remaining_farmers_for_war_spawn // 2
        sp_war_pairs = min(max_war_pairs_by_wheat, max_war_pairs_by_count)

        idx = 0

        # Assign farmers for spawning
        # First spawns: sp_farm_pairs * 2 farmers -> "spawn farmer"
        for _ in range(sp_farm_pairs * 2):
            if idx < len(farmers):
                final_group_for_farmer[farmers[idx]] = "spawn farmer"
                idx += 1

        # Next spawns: sp_war_pairs * 2 farmers -> "spawn warrior"
        for _ in range(sp_war_pairs * 2):
            if idx < len(farmers):
                final_group_for_farmer[farmers[idx]] = "spawn warrior"
                idx += 1

        # Remaining farmers -> stay in village to farm
        while idx < len(farmers):
            final_group_for_farmer[farmers[idx]] = "farm"
            idx += 1

        # Warriors: always move to the cave in village stage
        final_group_for_warrior = {w: "cave" for w in warriors}

        # Apply final assignments (exactly one assignment per component)
        for f, grp in final_group_for_farmer.items():
            environment.assign_group(f, grp)
        for w, grp in final_group_for_warrior.items():
            environment.assign_group(w, grp)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the cave, all Warriors should attack, Farmers return to the Village
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # Warriors attack
        for w in warriors:
            environment.assign_group(w, "attack")

        # Farmers go back to the Village
        for f in farmers:
            environment.assign_group(f, "village")
```