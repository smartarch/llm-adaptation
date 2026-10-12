Reasoning and adaptation strategy

Goal and constraints recap:
- All Warriors should end up in the Cave and then attack the Dragon.
- All Farmers should stay in the Village and farm or spawn new villagers (both Farmers and Warriors are needed).
- Spawning rules: to spawn a new Farm er, two villagers must be in the "spawn farmer" group and there must be at least 10 wheat; to spawn a new Warrior, two villagers must be in the "spawn warrior" group and there must be at least 12 wheat.
- The groups in the Village are: "farm" (stay in Village and farm), "cave" (go to the Cave), "spawn farmer" (trigger spawns of Farmers), "spawn warrior" (trigger spawns of Warriors).
- In the Cave, the groups are: "attack" (attack the Dragon), "cave" (stay in Cave), "village" (go to Village).
- You can read environment state (dragon hp, farm wheat) but you must use environment.assign_group(...) to assign groups.

Strategy description:
- In assign_in_village:
  - Default behavior: assign all Farmers to "farm" (stay in Village and farm) and all Warriors to "cave" (go to the Cave).
  - Exploit spawning opportunities without starving the army:
    - Determine how many Farmers to put into the "spawn farmer" group based on available wheat and the number of Farmers available. For each pair in the "spawn farmer" group, and 10 wheat, one new Farmer is spawned. We will target as many pairs as possible, up to the number of Farmers available in the village, and up to wheat // 10.
    - After allocating some Farmers to "spawn farmer" to satisfy as many Farmer spawns as possible, determine how many additional Warriors we can spawn using the remaining Farmers and the remaining wheat. For each pair in the "spawn warrior" group, and 12 wheat, one new Warrior is spawned. We will allocate pairs from Farmers still in the Village (those not currently in the "spawn farmer" group) up to the available wheat (remaining after the Farmer spawns).
  - Finally, issue the environment.assign_group calls for every Villager, using the computed group assignments.
- In assign_in_cave:
  - All Warriors should attack the Dragon, so assign them to "attack".
  - All Farmers should go back to the Village, so assign them to "village".
  - The "cave" group can be left empty or unused in this step (not required to be populated).

This strategy prioritizes immediate combat readiness (Warriors go to cave and then attack) while maximizing population growth via spawns using available wheat. Spawns are driven by simple, deterministic calculations based on current wheat and the number of eligible villagers, ensuring consistent behavior across steps.

Now the Python implementation:

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Expect group_ids to include: "farm", "cave", "spawn farmer", "spawn warrior"
        # Strategy:
        # - Farmers -> default to "farm"
        # - Warriors -> default to "cave"
        # - Spawn farmers: use pairs of Farmers in "spawn farmer" to spawn new Farmers, constrained by wheat
        # - Spawn warriors: use pairs of Farmers in "spawn warrior" to spawn new Warriors, constrained by remaining wheat
        mapping = {}

        # Separate by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Default assignments
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                mapping[c] = "cave"      # go to Cave
            else:
                mapping[c] = "farm"      # stay in Village and farm

        # Spawns planning (all decisions based on current environment wheat)
        wheat = getattr(getattr(environment, "farm", None), "wheat", 0)

        # Prepare lists after defaults
        farmers_in_farm = [f for f in farmers if mapping.get(f) == "farm"]

        # How many Farmer spawns can we do (max by wheat and by number of farmers in the farm group)
        max_farm_spawns_by_wheat = wheat // 10
        max_farm_spawns_by_count = len(farmers_in_farm) // 2
        max_farm_spawns = min(max_farm_spawns_by_wheat, max_farm_spawns_by_count)

        # Assign 2*max_farm_spawns Farmers to "spawn farmer"
        idx = 0
        for _ in range(max_farm_spawns):
            # pick next 2 farmers from the farm group
            if idx + 1 < len(farmers_in_farm):
                a = farmers_in_farm[idx]
                b = farmers_in_farm[idx + 1]
                mapping[a] = "spawn farmer"
                mapping[b] = "spawn farmer"
                idx += 2
            else:
                break

        # Recompute pool of farmers still in "farm" after assigning some to spawn farmer
        farmers_in_farm_after = [f for f in farmers if mapping.get(f) == "farm"]

        # Remaining wheat after Farmer spawns
        wheat_after_farm_spawns = wheat - max_farm_spawns * 10
        if wheat_after_farm_spawns < 0:
            wheat_after_farm_spawns = 0  # safety

        # Prepare list of farmers available for "spawn warrior" (still in "farm")
        available_for_warrior = farmers_in_farm_after

        max_warrior_spawns_by_wheat = wheat_after_farm_spawns // 12
        max_warrior_spawns_by_count = len(available_for_warrior) // 2
        max_warrior_spawns = min(max_warrior_spawns_by_wheat, max_warrior_spawns_by_count)

        # Assign 2*max_warrior_spawns Farmers to "spawn warrior" (from the remaining farm pool)
        idx = 0
        for _ in range(max_warrior_spawns):
            if idx + 1 < len(available_for_warrior):
                a = available_for_warrior[idx]
                b = available_for_warrior[idx + 1]
                mapping[a] = "spawn warrior"
                mapping[b] = "spawn warrior"
                idx += 2
            else:
                break

        # In case some farmers were not touched by spawns (still in "farm"), ensure they stay in "farm"
        for f in farmers:
            if f not in mapping:
                mapping[f] = "farm"

        # Apply assignments
        for component, gid in mapping.items():
            environment.assign_group(component, gid)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # Goal: Warriors attack, Farmers go back to Village
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                # Farmers go back to Village
                environment.assign_group(c, "village")
```