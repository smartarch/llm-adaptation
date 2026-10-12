Strategy and reasoning (task analysis)

- Objective recap:
  - Kill the Dragon as fast as possible.
  - All Warriors must go to the Cave to attack.
  - All Farmers should stay in the Village (but can be used to spawn new villagers and generate wheat).
  - Spawn groups “spawn farmer” and “spawn warrior” create new villagers provided there is enough wheat:
    - spawn farmer: for every 2 villagers in this group and at least 10 wheat in the Farm, a new Farmer is spawned.
    - spawn warrior: for every 2 villagers in this group and at least 12 wheat in the Farm, a new Warrior is spawned.
  - The Dragon can counterattack; we want to ensure we attack early (at least once in the first 15 steps).
  - All Warriors should be in the Cave, and at least half of them should be in the Cave most of the time so they can attack promptly.

- High-level adaptation plan:
  1. In assign_in_village:
     - Move all Warriors to the Cave immediately (so they will attack once we reach the cave step).
     - Keep Farmers in the Village by default (in group "farm"), but also purposely designate small spawn groups using some Farmers to spawn new villagers, using Wheat in the Farm as a resource.
     - Use Wheat to decide whether we can spawn new Farmers or Warriors. If Wheat is abundant (e.g., 10+ for a Farmer spawn, and 12+ for a Warrior spawn) and we have enough Farmers to spare, allocate 2 Farmers to each of the spawn groups (when possible). The remaining Farmers stay in the Farm group to continue producing Wheat.
     - Ensure there are at least 2 Farmers in the Farm group when possible so wheat can accumulate to fuel future spawns.
  2. In assign_in_cave:
     - Reassign all Villagers currently in the Cave:
       - Warriors -> "attack" (they will attack the Dragon).
       - Farmers -> return to the Village ("village" group). This keeps Farmers in Village as required.
     - This guarantees all Warriors are attacking the Dragon while Farmers stay in the Village, ready to farm or spawn in subsequent steps.

- Why this approach satisfies constraints:
  - All Warriors are moved to the Cave (in village step) and then attack (in cave step).
  - All Farmers are kept in Village (in village step) and then sent back to Village (in cave step), fulfilling the “Farmers should stay in Village” requirement.
  - Spawning is driven by wheat availability; we attempt to spawn several new villagers to increase the chance of killing the Dragon, while ensuring wheat is consumed only when available per 10 Wheat for farmers and 12 Wheat for warriors spawning in the Farm.
  - Initial attack is guaranteed by moving Warriors to cave and then to attack in the first cave decision.
  - At least half of the Warriors are in the Cave (in our design, all Warriors go to Cave and attack, which satisfies the “at least half” requirement; the other Warriors (spawned later) will be directed to the Cave in subsequent steps).

Code (Python) implementing the adaptation strategy

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Split villagers in village into Farmers and Warriors
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Decide farming vs spawning allocations for Farmers
        farm_to_place = 0
        if len(farmers) > 0:
            farm_to_place = max(1, int(len(farmers) * 0.6))
            if farm_to_place > len(farmers):
                farm_to_place = len(farmers)

        remaining = len(farmers) - farm_to_place
        farm_wheat = getattr(environment.farm, "wheat", 0)

        spawn_farmer = 0
        spawn_warrior = 0

        # Attempt to allocate spawns if wheat allows
        if remaining >= 2 and farm_wheat >= 10:
            spawn_farmer = min(2, remaining)
            remaining -= spawn_farmer
        if remaining >= 2 and farm_wheat >= 22:
            # If we have enough wheat left, spawn two warriors as well
            spawn_warrior = min(2, remaining)

        # Build index sets to assign groups deterministically
        farm_indices = set(range(0, farm_to_place))
        spawn_farmer_indices = set(range(farm_to_place, farm_to_place + spawn_farmer))
        spawn_warrior_indices = set(range(farm_to_place + spawn_farmer,
                                         farm_to_place + spawn_farmer + spawn_warrior))

        # Assign Farmers to their respective groups
        for idx, farmer in enumerate(farmers):
            if idx in farm_indices:
                group = "farm"
            elif idx in spawn_farmer_indices:
                group = "spawn farmer"
            elif idx in spawn_warrior_indices:
                group = "spawn warrior"
            else:
                # Fallback: keep in farm
                group = "farm"
            environment.assign_group(farmer, group)

        # All Warriors go to the Cave to prepare for attack
        for w in warriors:
            environment.assign_group(w, "cave")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the cave, send Warriors to attack and bring Farmers back to Village
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                # Farmers return to the Village
                environment.assign_group(c, "village")
```