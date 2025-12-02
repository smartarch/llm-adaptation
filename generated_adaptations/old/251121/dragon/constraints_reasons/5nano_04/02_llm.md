Strategy reasoning and plan:
- Goal alignment:
  - All Warriors should go to the Cave and then attack the Dragon.
  - All Farmers should stay in the Village.
  - Spawn a modest number of new Farmers and Warriors to increase DPS and wheat production, ensuring we have enough forces to threaten the Dragon early.
  - Attack the Dragon early (within the first 15 steps) by moving at least some Warriors into the attack group as soon as possible.
  - Keep at least half of the Warriors in the Cave so they can contribute to attacks in subsequent turns.

- How to realize this:
  - In assign_in_village:
    - Move all Warriors to the Cave so they can travel there and later attack.
    - Keep all Farmers in the Village by default in the "farm" group.
    - Use the spawn groups to generate new villagers, constrained by available wheat:
      - spawn farmer: requires 2 villagers in the group and 10 wheat -> spawns a new Farmer. We will try to spawn up to 3 Farmers this way, limited by available wheat and number of Farmers available to assign to the spawn Farmer group (2 per new Farmer).
      - spawn warrior: requires 2 villagers in the group and 12 wheat -> spawns a new Warrior. We will try to spawn up to 2 Warriors this way, constrained by the remaining Wheat and the number of Farmers available to assign to the spawn Warrior group (2 per new Warrior).
    - After allocating to the spawn groups, remaining Farmers stay in the Farm group.
  - In assign_in_cave:
    - Move all Warriors to the "attack" group so they attack the Dragon.
    - Move any Farmers in the Cave back to the Village by assigning them to the "village" group, ensuring Farmers stay in the Village.
  - This structure guarantees:
    - Warriors travel to Cave and attack (fulfills the primary requirement).
    - Farmers remain in Village (or return there if temporarily in Cave).
    - Spawned villagers increase the pool of both Farmers and Warriors over time.
    - An attack is present from step 0 (as soon as Warriors are moved to the Cave and then into the attack group).

- Robustness notes:
  - The logic uses environment.farm.wheat to gauge spawning capacity, and it caps spawns to avoid over-spawning.
  - If there isn’t enough wheat or not enough villagers to satisfy the “two villagers per spawn” rule, spawning is skipped gracefully.
  - The code targets a modest growth: up to 3 new Farmers and up to 2 new Warriors per village step, subject to resources.

Python implementation:

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate farmers and warriors in the village
        farmers = [c for c in components if getattr(c, 'role', None) == 'Farmer']
        warriors = [c for c in components if getattr(c, 'role', None) == 'Warrior']

        # 1) All warriors should go to the Cave
        for w in warriors:
            environment.assign_group(w, 'cave')

        # 2) Farmers stay in the Village by default (farm)
        # Attempt to spawn new villagers using the spawn groups, constrained by wheat.
        wheat = 0
        try:
            wheat = environment.farm.wheat
        except Exception:
            wheat = 0

        # Spawn plan
        # - Farmer spawns: up to 3, 10 wheat each, requires 2 farmers per spawn
        max_farm_spawns_by_wheat = wheat // 10
        max_farm_spawns_by_people = len(farmers) // 2
        spawn_farmers = int(min(3, max_farm_spawns_by_wheat, max_farm_spawns_by_people))

        # Allocate 2*spawn_farmers farmers to the "spawn farmer" group
        assigned_to_spawn_farm = farmers[:spawn_farmers * 2]
        for f in assigned_to_spawn_farm:
            environment.assign_group(f, 'spawn farmer')

        remaining_farmers = farmers[spawn_farmers * 2:]

        # - Warrior spawns: up to 2, 12 wheat each, requires 2 farmers per spawn
        max_war_spawns_by_wheat = wheat // 12
        max_war_spawns_by_people = len(remaining_farmers) // 2
        spawn_warriors = int(min(2, max_war_spawns_by_wheat, max_war_spawns_by_people))

        assigned_to_spawn_warrior = remaining_farmers[:spawn_warriors * 2]
        for f in assigned_to_spawn_warrior:
            environment.assign_group(f, 'spawn warrior')

        remaining_farmers_after_spawns = remaining_farmers[spawn_warriors * 2:]

        # The rest of farmers go to farming in the village
        for f in remaining_farmers_after_spawns:
            environment.assign_group(f, 'farm')

        # Note: Any other villagers that are not Farmers/Warriors should be left in their default state.

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the cave, all Warriors should attack; Farmers should go back to village.
        for c in components:
            if getattr(c, 'role', None) == 'Warrior':
                environment.assign_group(c, 'attack')
            else:
                # Farmers return to the village
                environment.assign_group(c, 'village')
```