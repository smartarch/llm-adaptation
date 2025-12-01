Reasoning and improved adaptation strategy

What went wrong before:
- All Farmers were kept in the Village (farm group) and no initial force was sent to the Cave to start damaging the Dragon. With the Dragon starting at 50 HP, this led to zero or extremely slow progress and a likely loss within 30 steps.

Key improvements in the new strategy:
- Start attacking early: Move a small but meaningful number of Farmers to the Cave to begin dealing damage (attack power from Farmers is 1 per step).
- Maintain a spawning pipeline: Use Wheat from the Farm to spawn new Farmers and Warriors, but do it in a controlled, step-by-step fashion so we don’t starve the attack force.
- Dynamic spawning plan:
  - First, spawn as many Farmers as allowed by wheat (10 wheat per new Farmer), using pairs of Farmers in the spawn farmer group.
  - Then, with remaining Wheat, spawn Warriors (12 wheat per new Warrior) using pairs of Farmers in the spawn warrior group.
- In the Cave, keep Warriors credited to attack, and rotate Farmers back to Village after their cave exposure to maintain farming and spawning capacity.

How this translates to code:
- assign_in_village:
  - Move a small number of Farmers to cave to start attacking.
  - Use remaining Farmers to populate spawn groups as wheat allows, first for farmers, then for warriors.
  - Any unassigned Farmers stay in Farm.
  - All group assignments are done through environment.assign_group(...).
- assign_in_cave:
  - All Warriors go to attack.
  - All Farmers in the Cave go back to Village (to continue farming/spawning next steps).

This approach aims to produce visible Dragon damage within the first few turns while keeping a steady flow of wheat-backed spawns to scale the fighting force over time.

Code implementation:

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Strategy:
        # - Start attacking by sending a small number of Farmers to the Cave.
        # - Use Wheat to spawn Farmers first, then Warriors, using pairs of villagers.
        # - Leave any remaining villagers in Farm.

        mapping = {}

        # Step 1: initial attack push - move up to 3 Farmers to cave to start dealing damage
        # (if there are fewer than 3 villagers, move as many as available)
        initial_attackers = min(3, len(components))
        for i, c in enumerate(components):
            if i < initial_attackers:
                mapping[c] = "cave"  # go to Cave and attack as Farmers (attack power 1)
            else:
                mapping[c] = "farm"

        # Step 2: spawning planning based on wheat in farm
        wheat = 0
        if hasattr(environment, "farm") and hasattr(environment.farm, "wheat"):
            wheat = getattr(environment.farm, "wheat", 0)

        # Pool of villagers available for spawning (those not currently assigned to cave)
        farmers_for_spawn = [c for c in components if mapping.get(c) != "cave"]

        # Spawn Farmer: needs 2 villagers in spawn farmer and 10 wheat
        max_farm_spawns_by_wheat = wheat // 10
        max_farm_spawns_by_count = len(farmers_for_spawn) // 2
        max_farm_spawns = min(max_farm_spawns_by_wheat, max_farm_spawns_by_count)

        # Assign 2 villagers per Farmer spawn to "spawn farmer"
        idx = 0
        for _ in range(max_farm_spawns):
            if idx + 1 < len(farmers_for_spawn):
                a = farmers_for_spawn[idx]
                b = farmers_for_spawn[idx + 1]
                mapping[a] = "spawn farmer"
                mapping[b] = "spawn farmer"
                idx += 2
            else:
                break

        # Recompute wheat after farmer spawns
        wheat_after_farm_spawns = wheat - max_farm_spawns * 10
        if wheat_after_farm_spawns < 0:
            wheat_after_farm_spawns = 0

        # Spawn Warrior: needs 2 villagers in spawn warrior and 12 wheat
        remaining_for_warrior = [c for c in components if mapping.get(c) != "spawn farmer" and mapping.get(c) != "cave"]
        # Those remaining_for_warrior are effectively in "farm" now

        max_warrior_spawns_by_wheat = wheat_after_farm_spawns // 12
        max_warrior_spawns_by_count = len(remaining_for_warrior) // 2
        max_warrior_spawns = min(max_warrior_spawns_by_wheat, max_warrior_spawns_by_count)

        idx = 0
        for _ in range(max_warrior_spawns):
            if idx + 1 < len(remaining_for_warrior):
                a = remaining_for_warrior[idx]
                b = remaining_for_warrior[idx + 1]
                mapping[a] = "spawn warrior"
                mapping[b] = "spawn warrior"
                idx += 2
            else:
                break

        # Ensure any villager not yet assigned gets a default grouping
        for c in components:
            if c not in mapping:
                mapping[c] = "farm"

        # Apply the group assignments
        for component, gid in mapping.items():
            environment.assign_group(component, gid)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave:
        # - Warriors should attack the Dragon
        # - Farmers should return to the Village
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```