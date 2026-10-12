Reasoning and adaptation strategy

Goal and constraints
- All Warriors should go to the Cave and then attack the Dragon.
- All Farmers should stay in the Village and either farm (to produce wheat) or participate in spawning new villagers (both Farmers and Warriors are necessary to keep the population growing and the DPS scalable).
- Spawning rules: 
  - spawn farmer: for every two villagers assigned to the "spawn farmer" group and 10 wheat, a new Farmer is spawned.
  - spawn warrior: for every two villagers assigned to the "spawn warrior" group and 12 wheat, a new Warrior is spawned.
- We want to maximize DPS against the Dragon while maintaining wheat production to enable growth via spawning, and ensure we don’t run out of villagers before the 30-step limit.
- The Dragon has 50 HP and can damage villagers in the Cave; we should get our Warriors to the Cave to attack as soon as possible, while Farmers keep farming or spawning to replenish and increase DPS over time.

Strategy
- In village:
  - Move all Warriors to the Cave (to eventually attack).
  - For Farmers, split the group into three subgroups:
    - spawn farmer: two farmers per potential spawn, consuming 10 wheat per spawn; these villagers stay in the village to trigger additional Farmers.
    - spawn warrior: two villagers per potential spawn, consuming 12 wheat per spawn; these villagers stay in the village to trigger additional Warriors.
    - farm: all remaining Farmers stay in the Village to farm wheat.
  - The number of spawns is limited by both available Farmers and Wheat:
    - spawns_farm = min(number_of_farmers_in_village // 2, farm_wheat // 10)
    - After allocating spawns_farm, compute remaining wheat and allocate spawns_warrior = min(remaining_farmers // 2, remaining_wheat // 12)
- In cave:
  - Move Warriors to the Attack group to participate in the Dragon fight.
  - Move Farmers to the Village (they should return to farming/spawning next cycle).

This approach ensures Warriors are always contributing DPS in the cave, while Farmers are productive (farming) and also capable of creating additional villagers when there is enough wheat, enabling exponential growth potential within the 30-step constraint.

Python implementation

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Groups
        farm_group = "farm"
        cave_group = "cave"           # move to cave
        spawn_farmer = "spawn farmer"
        spawn_warrior = "spawn warrior"

        # Separate farmers and warriors currently in the village
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # 1) All Warriors should go to the Cave (to be able to attack later)
        for c in warriors:
            environment.assign_group(c, cave_group)

        # 2) Plan spawning for Farmers
        # Wheat available for spawning
        wheat = environment.farm.wheat

        # How many farmer spawns can we trigger this step?
        spawns_farm = min(len(farmers) // 2, wheat // 10)

        # Allocate 2*spawns_farm farmers to the "spawn farmer" group
        farmers_for_spawn_farm = farmers[:2 * spawns_farm]
        for c in farmers_for_spawn_farm:
            environment.assign_group(c, spawn_farmer)

        # Remaining farmers after allocating to spawn farmer
        remaining_farmers = farmers[2 * spawns_farm:]

        # Wheat left after allocating for farmer spawns
        wheat_left_after_farm = wheat - spawns_farm * 10

        # How many warrior spawns can we trigger this step from the remaining farmers?
        spawns_warrior = min(len(remaining_farmers) // 2, wheat_left_after_farm // 12)

        # Allocate 2*spawns_warrior farmers to the "spawn warrior" group
        farmers_for_spawn_warrior = remaining_farmers[:2 * spawns_warrior]
        for c in farmers_for_spawn_warrior:
            environment.assign_group(c, spawn_warrior)

        # The remaining farmers (not allocated to spawn groups) stay in farm
        farmers_for_farm = remaining_farmers[2 * spawns_warrior:]
        for c in farmers_for_farm:
            environment.assign_group(c, farm_group)

        # Note: Any farmers already assigned to spawn groups are no longer assigned to farm_group.

        # If there are no farmers or wheat, ensure at least one sensible default (all farmers already handled)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # Groups
        attack_group = "attack"
        cave_group = "cave"
        village_group = "village"

        for c in components:
            # If a Warrior is in the cave, send them to attack.
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, attack_group)
            else:
                # Farmers in cave should return to the village (farmers stay in village to farm/spawn)
                environment.assign_group(c, village_group)
```