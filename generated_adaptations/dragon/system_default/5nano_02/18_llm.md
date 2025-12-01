Reasoning and improved adaptation strategy

Goal recap
- All Warriors should end up in the Cave and attack the Dragon.
- Farmers stay in the Village to farm or spawn new villagers (both Farmers and Warriors are needed).
- Spawning rules: for every two villagers assigned to spawn farmer and 10 wheat, a new Farmer is spawned; for every two villagers assigned to spawn warrior and 12 wheat, a new Warrior is spawned.
- You win by reducing the Dragon’s HP to 0 within 30 steps; you lose if the Dragon survives or all villagers die.

Key ideas to improve chances
- Manage cave occupancy carefully to balance early DPS with survival. The Dragon can attack back and can eat villagers in the Cave. Keeping the cave occupancy modest reduces risk while still providing DPS.
- Maintain a steady spawning pipeline: first spawn Farmers (needs 10 wheat per new Farmer, using pairs of villagers in the village) to sustain wheat-to-population growth, then spawn Warriors (needs 12 wheat per new Warrior, again using pairs). This ensures growth without starving the attack force.
- Use a simple, environment-driven rule set:
  - Always keep all Warriors in the Cave (as required).
  - Dynamically cap the number of Farmers moved to the Cave as a function of Dragon HP, so we inject early DPS but avoid excessive casualties when the Dragon is strong.
  - When there is room in the Cave (below the cap), move Farmers from the Village into the Cave up to the cap.
  - Then allocate wheat to spawn groups (farmers first, then warriors) using pairs from the available village pool.
- This approach aims for a reliable DPS contribution while preserving a steady growth loop via spawns, and it explicitly caps cave occupancy to reduce risk.

Python implementation

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Divide Villagers in the Village into:
        - farm: stay in Village and farm
        - cave: go to the Cave (to attack)
        - spawn farmer: for every two villagers assigned here and 10 wheat, spawn a new Farmer
        - spawn warrior: for every two villagers assigned here and 12 wheat, spawn a new Warrior
        """
        mapping = {}

        # Read current dragon HP to adapt aggressiveness
        dragon_hp = getattr(getattr(environment, "dragon", None), "hp", 0)

        # Cap the number of Farmers we move to the Cave to balance DPS vs risk
        # Dynamic cap: more aggressive when dragon is healthy, conservative when weak
        if dragon_hp >= 40:
            cave_cap = 2
        elif dragon_hp >= 25:
            cave_cap = 2
        else:
            cave_cap = 1

        # Default assignments: Warriors -> cave, Farmers -> farm
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                mapping[c] = "cave"
            else:
                mapping[c] = "farm"

        # Step: Move up to cave_cap Farmers to Cave for initial DPS
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        movable_farmers = [f for f in farmers if mapping.get(f) != "cave"]

        moved = 0
        for f in movable_farmers:
            if moved >= cave_cap:
                break
            mapping[f] = "cave"
            moved += 1

        # Step 2: Spawning planning based on wheat in the Farm
        wheat = getattr(getattr(environment, "farm", None), "wheat", 0)

        # Pool of villagers currently in Village (not in Cave)
        village_pool = [c for c in components if mapping.get(c) != "cave"]

        # Spawn Farmers: needs 2 villagers in spawn farmer + 10 wheat
        max_farm_spawns_by_wheat = wheat // 10
        max_farm_spawns_by_count = len(village_pool) // 2
        max_farm_spawns = min(max_farm_spawns_by_wheat, max_farm_spawns_by_count)

        idx = 0
        for _ in range(max_farm_spawns):
            a = village_pool[idx]
            b = village_pool[idx + 1]
            mapping[a] = "spawn farmer"
            mapping[b] = "spawn farmer"
            idx += 2

        wheat_after_farm_spawns = wheat - max_farm_spawns * 10
        if wheat_after_farm_spawns < 0:
            wheat_after_farm_spawns = 0

        # Spawn Warriors: needs 2 villagers in spawn warrior + 12 wheat
        pool_for_warrior = [c for c in components if mapping.get(c) not in ("spawn farmer", "cave")]
        max_warrior_spawns = min(wheat_after_farm_spawns // 12, len(pool_for_warrior) // 2)

        idx = 0
        for _ in range(max_warrior_spawns):
            a = pool_for_warrior[idx]
            b = pool_for_warrior[idx + 1]
            mapping[a] = "spawn warrior"
            mapping[b] = "spawn warrior"
            idx += 2

        # Fallback for any remaining unassigned villagers
        for c in components:
            if c not in mapping:
                mapping[c] = "farm"

        # Apply assignments
        for component, gid in mapping.items():
            environment.assign_group(component, gid)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave:
        # - Warriors attack
        # - Farmers go back to Village
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```