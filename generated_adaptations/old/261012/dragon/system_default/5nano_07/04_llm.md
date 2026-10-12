Reasoning and improved strategy

Goal recap and new constraints
- We still must ensure all Warriors eventually go to the Cave and attack the Dragon, but we can stage their arrival to reduce the risk from the Dragon’s counterattacks (which hit every Villager in the Cave).
- Farmers should stay in the Village to farm wheat and to trigger spawning of new Farmers and Warriors when there is enough wheat.
- Spawning rules remain the same:
  - spawn farmer: for every two Villagers assigned to "spawn farmer" and 10 wheat, a new Farmer is spawned.
  - spawn warrior: for every two Villagers assigned to "spawn warrior" and 12 wheat, a new Warrior is spawned.

Key improvements over the previous approach
- Phased assault: Instead of sending all Warriors to the Cave immediately, we send a small batch each step (e.g., 1–3 depending on the step) to gradually build up force in the Cave. This reduces the probability of catastrophic losses due to Dragon attacks while still ramping up DPS over time.
- Continuous wheat-based spawning: Farmers continue to farm wheat and we use that wheat to spawn new villagers in a way that prioritizes producing more Farmers early (to sustain growth) and then Warriors if wheat allows.
- Farmers in Cave get moved back to Village: To align with the rule that Farmers should stay in the Village (for farming/spawning), any Farmers found in the Cave are moved back to the Village.

Strategy outline
- In assign_in_village:
  - Identify Warriors in the Village and send a small, step-dependent batch to the Cave (attack gradually).
  - Use available wheat to spawn new Farmers and Warriors, prioritizing spawning in a way that keeps enough Farmers to continue wheat production.
  - The remaining Farmers stay in the Village and are assigned to farm or spawn groups as appropriate.
- In assign_in_cave:
  - Move all Warriors currently in the Cave to the Attack group.
  - Move any Farmers currently in the Cave back to the Village (they should farm or spawn from there).

This phased approach aims to achieve earlier, sustainable DPS growth while mitigating risk from Dragon counterattacks and maintaining wheat production for ongoing growth.

Python implementation

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        farm_group = "farm"
        cave_group = "cave"
        spawn_farmer = "spawn farmer"
        spawn_warrior = "spawn warrior"

        # Separate Farmers and Warriors currently in the Village
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Phased assault: send a small batch of Warriors to the Cave this step
        attack_batch = 0
        if len(warriors) > 0:
            if step < 3:
                attack_batch = 1
            elif step < 6:
                attack_batch = min(2, len(warriors))
            else:
                attack_batch = min(3, len(warriors))

        for i in range(attack_batch):
            environment.assign_group(warriors[i], cave_group)

        # Spawning logic using Wheat in the Farm
        wheat = getattr(environment.farm, "wheat", 0)

        # Farmers available to spawn
        # Note: Warriors moved to cave are no longer in this village list for this step
        spawns_farm = min(len(farmers) // 2, wheat // 10)

        # Assign 2*spawns_farm farmers to the "spawn farmer" group
        for c in farmers[:2 * spawns_farm]:
            environment.assign_group(c, spawn_farmer)

        # Wheat left after farmer spawns
        wheat_after_farm = wheat - spawns_farm * 10
        remaining_after_farm = farmers[2 * spawns_farm:]

        # Spawn warriors from the remaining farmers if wheat allows
        spawns_warrior = min(len(remaining_after_farm) // 2, wheat_after_farm // 12)

        for c in remaining_after_farm[:2 * spawns_warrior]:
            environment.assign_group(c, spawn_warrior)

        remaining_after_warrior = remaining_after_farm[2 * spawns_warrior:]

        # The rest stay in Farm (Farmers continue farming)
        for c in remaining_after_warrior:
            environment.assign_group(c, farm_group)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        attack_group = "attack"
        cave_group = "cave"
        village_group = "village"

        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, attack_group)
            else:
                # Farmers in the Cave should retreat to the Village to farm/spawn
                environment.assign_group(c, village_group)
```