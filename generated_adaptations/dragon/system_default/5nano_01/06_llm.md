Reasoning and adaptation strategy

New approach goal:
- Increase DPS quickly while preserving enough wheat production to sustain spawning.
- Prioritize creating more Warriors early because they deal more damage, accelerating Dragon HP reduction.
- Maintain a small, steady wheat production base by keeping a minimal number of Farmers farming, but still allocate enough Farmers to spawn new villagers when possible.
- Use a step-aware tactic: early steps favor farming to build up wheat; mid-to-late steps tilt toward spawning Warriors to boost DPS.

Key changes from prior approach:
- In village, Warriors still go to the Cave to attack.
- Farmers are allocated with a dynamic plan:
  - Reserve a small core of Farmers to keep farming (min_keep_farming depends on step).
  - Use as many remaining Farmers as possible to spawn Warriors first (spawn warrior: 2 Farmers + 12 wheat).
  - Use remaining Farmers to spawn Farmers (spawn farmer: 2 Farmers + 10 wheat).
  - Any leftover Farmers default to farming.
- This makes the Dragon DPS grow faster earlier, while still generating Wheat for future spawns.
- In the Cave, behavior remains: Warriors attack, Farmers return to Village.

Python implementation:

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Split villagers in village into:
        # - farm: stay in Village and farm
        # - spawn farmer: for every two villagers and 10 wheat, spawn a new Farmer
        # - spawn warrior: for every two villagers and 12 wheat, spawn a new Warrior

        # Collect villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # All Warriors should head to the cave (attack)
        for w in warriors:
            environment.assign_group(w, "cave")

        # Wheat available for spawning
        wheat = getattr(getattr(environment, "farm", None), "wheat", 0)

        # Dynamic minimum farming retention based on step
        if len(farmers) <= 1:
            min_keep_farming = len(farmers)
        else:
            if step < 18:
                min_keep_farming = min(3, len(farmers) - 2)
            elif step < 26:
                min_keep_farming = min(4, len(farmers) - 2)
            else:
                min_keep_farming = max(0, min(3, len(farmers) - 2))

        idx = 0

        # 1) Assign core farmers to farming
        for _ in range(min_keep_farming):
            if idx < len(farmers):
                environment.assign_group(farmers[idx], "farm")
                idx += 1

        remaining_farmers = len(farmers) - idx

        # 2) Determine how many Warriors we can spawn now
        max_war_spawns = 0
        if remaining_farmers >= 2 and wheat >= 12:
            max_war_spawns = min(remaining_farmers // 2, wheat // 12)

        # 3) Allocate spawn warrior pairs (prioritize DPS)
        for _ in range(max_war_spawns):
            if idx + 1 >= len(farmers):
                break
            environment.assign_group(farmers[idx], "spawn warrior")
            environment.assign_group(farmers[idx + 1], "spawn warrior")
            idx += 2

        remaining_farmers_after_war = len(farmers) - idx
        wheat_after_war = max(0, wheat - (max_war_spawns * 12))

        # 4) Determine how many Spawn Farmer pairs we can form with the remaining farmers
        max_farm_spawns = 0
        if remaining_farmers_after_war >= 2 and wheat_after_war >= 10:
            max_farm_spawns = min(remaining_farmers_after_war // 2, wheat_after_war // 10)

        # 5) Allocate spawn farmer pairs
        for _ in range(max_farm_spawns):
            if idx + 1 >= len(farmers):
                break
            environment.assign_group(farmers[idx], "spawn farmer")
            environment.assign_group(farmers[idx + 1], "spawn farmer")
            idx += 2

        # 6) Remaining farmers farm
        while idx < len(farmers):
            environment.assign_group(farmers[idx], "farm")
            idx += 1

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave:
        # - Warriors go to attack
        # - Farmers go back to Village
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```