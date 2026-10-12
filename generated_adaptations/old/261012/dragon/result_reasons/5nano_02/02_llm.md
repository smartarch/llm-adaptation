Reasoning and adaptation strategy

Goal and constraints recap:
- All Warriors must go to the Cave to attack the Dragon.
- All Farmers stay in the Village and can farm (produce wheat) or be used to spawn new villagers.
- Spawning rules: In the Village, two villagers assigned to "spawn farmer" with at least 10 wheat spawn a new Farmer; two villagers assigned to "spawn warrior" with at least 12 wheat spawn a new Warrior.
- We want to attack early (at least once in the first 15 steps) and ensure the Dragon dies within 30 steps.
- We also want to keep at least half of Warriors ready to attack (in Cave) most of the time.

Strategy description:
- In assign_in_village:
  - Move all existing Warriors in the Village to the Cave so they can attack the Dragon as soon as possible. This guarantees a quick first attack and keeps Warriors ready for subsequent attacks.
  - Farmers stay in the Village. We use a simple, deterministic spawning heuristic to create a few extra Farmers and Warriors, provided there is enough wheat and enough villagers to allocate to the spawn groups.
  - Spawns are allocated from Farmers in the Village. We attempt to spawn up to:
    - 2 new Farmers if there are at least 4 Farmers and at least 20 wheat (consuming 4 villagers and 20 wheat).
    - If best possible after that, 1 new Warrior if we have at least 2 remaining Farmers and at least 12 wheat left.
  - The spawning process uses 2 Farmers per spawn (as required) and assigns those farmers to the corresponding spawn group ("spawn farmer" or "spawn warrior"). The remaining Farmers, if any, are assigned to the usual "farm" group to continue producing wheat.
  - Any Warriors present in the Village will be moved to the Cave (they will attack in the Cave in the next phase).

- In assign_in_cave:
  - Move all Farmers present in the Cave back to the Village (to stay in the Village per requirement).
  - Move all Warriors present in the Cave to the "attack" group so they will attack the Dragon.
  - This ensures Warri ors in Cave attack, Farmers stay in Village, and the Dragon is attacked as soon as possible.

This approach ensures:
- Immediate attack potential in Step 0 by moving Warriors to Cave.
- A modest amount of growth via spawning to increase DPS (both farmers and warriors) as wheat permits.
- All Warriors spend time in the Cave (attack-capable) while Farmers stay in Village to maintain farming and spawning capability.
- The Dragon should be attacked early and frequently, improving the chance to kill within 30 steps.

Python code (class SmartAdaptation)

```py
import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Strategy:
        # - Move all Warriors in Village to Cave (to ensure attack capability)
        # - Farm the Farmers in Village
        # - Spawn a small number of new Farmers and Warriors if wheat/resources allow
        # - Use remaining Farmers to farm

        # Separate by role
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # 1) Move all existing Warriors in Village to Cave
        for w in warriors:
            environment.assign_group(w, "cave")

        # After this, remaining villagers in Village are only Farmers (if any)
        # 2) Spawning decision based on available wheat and number of farmers
        available_wheat = environment.farm.wheat

        F_spawns = 0
        W_spawns = 0

        # Simple deterministic heuristic:
        # - If we can, spawn 2 Farmers (needs 4 farmers and 20 wheat)
        if len(farmers) >= 4 and available_wheat >= 20:
            F_spawns = 2
            available_wheat -= 20
        else:
            # else, try to spawn 1 Farmer if possible (needs 2 farmers and 10 wheat)
            if len(farmers) >= 2 and available_wheat >= 10:
                F_spawns = 1
                available_wheat -= 10

        # After farmer spawns, try to spawn 1 Warrior if we have enough remaining farmers and wheat
        remaining_farmers_for_warrior = len(farmers) - (2 * F_spawns)
        if remaining_farmers_for_warrior >= 2 and available_wheat >= 12:
            W_spawns = 1
            available_wheat -= 12

        # Ensure we do not exceed available farmers when assigning spawn groups
        total_needed_spawn_villagers = 2 * (F_spawns + W_spawns)
        if total_needed_spawn_villagers > len(farmers):
            # Reduce spawns proportionally, preferring Farmer spawns
            max_pairs = len(farmers) // 2
            F_spawns = min(F_spawns, max_pairs)
            W_spawns = min(W_spawns, max(0, max_pairs - F_spawns))
            total_needed_spawn_villagers = 2 * (F_spawns + W_spawns)

        # 3) Assign spawns from farmers
        idx = 0
        # Spawn Farmers
        for _ in range(F_spawns):
            environment.assign_group(farmers[idx], "spawn farmer")
            environment.assign_group(farmers[idx + 1], "spawn farmer")
            idx += 2
        # Spawn Warriors
        for _ in range(W_spawns):
            environment.assign_group(farmers[idx], "spawn warrior")
            environment.assign_group(farmers[idx + 1], "spawn warrior")
            idx += 2

        # 4) Remaining farmers go to farming
        for i in range(idx, len(farmers)):
            environment.assign_group(farmers[i], "farm")

        # Note: Any Warriors already moved to Cave at the start remain in the Cave
        # and will be handled in assign_in_cave.

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # Strategy in Cave:
        # - All Warriors in Cave should attack Dragon
        # - All Farmers in Cave should go back to Village (stay in Village)

        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                # Farmers (and any non-Warrior) should return to Village
                environment.assign_group(c, "village")
```