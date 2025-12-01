Reasoning and improved adaptation strategy

Goal and context recap:
- All Warriors should end up in the Cave and attack the Dragon.
- Farmers stay in the Village to farm or spawn new villagers (both Farmers and Warriors are needed).
- Spawning rules: for every two villagers assigned to "spawn farmer" and 10 wheat, a new Farmer is spawned; for every two villagers assigned to "spawn warrior" and 12 wheat, a new Warrior is spawned.
- You win by reducing the Dragon’s HP to 0 within 30 steps; you lose if the Dragon survives or all villagers die.

What we change and why
- Dynamic aggressiveness based on Dragon HP: push a small number of Farmers to the Cave early when the Dragon is healthy to start dealing damage sooner, but scale back as the Dragon weakens to reduce risk from dragon retaliation.
- Maintain a steady spawning pipeline in the Village: spawn Farmers first (with 10 wheat per new Farmer) and then spawn Warriors (with 12 wheat per new Warrior). This keeps a sustainable growth of both DPS and population.
- Always keep Warriors in the Cave (attack) and send Farmers back to the Village after Cave turns (as required by the rules).
- Use a simple, deterministic decision process that references the current environment (dragon HP and wheat) to decide how many Farmers to send to the Cave and how many to allocate to spawning groups.

What you’ll see
- assign_in_village:
  - Compute a small dynamic number of Farmers to send to the Cave based on Dragon HP (more aggressive when HP is high, smaller when HP is low).
  - Use remaining farmers to form spawn farmer groups (in pairs) as wheat allows.
  - Use remaining village farmers (not in cave or spawn farmer) to form spawn warrior groups (in pairs) as wheat allows.
  - Leave leftovers in Farm.
- assign_in_cave:
  - Warriors attack and Farmers return to Village.

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

        # Determine how many Farmers to send to Cave for early DPS (dynamic)
        # More aggressive when dragon_hp is high; conservative as it weakens
        if dragon_hp >= 40:
            n_to_cave = min(3, len(components))
        elif dragon_hp >= 25:
            n_to_cave = min(2, len(components))
        else:
            n_to_cave = min(1, len(components))

        # Default assignments
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                mapping[c] = "cave"  # Warriors go to Cave
            else:
                mapping[c] = "farm"  # Farmers stay in Village

        # Step: Move up to n_to_cave Farmers to Cave for initial DPS
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        movable_farmers = [f for f in farmers if mapping.get(f) != "cave"]

        moved = 0
        for f in movable_farmers:
            if moved >= n_to_cave:
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