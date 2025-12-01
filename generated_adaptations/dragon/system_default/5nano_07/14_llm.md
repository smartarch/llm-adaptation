Reasoning and improved strategy

Goal recap
- Warriors must eventually reach the Cave and attack the Dragon.
- Farmers should stay in the Village to farm and enable spawning (both Farmers and Warriors).
- Spawning rules remain:
  - spawn farmer: 2 villagers in the “spawn farmer” group and 10 wheat
  - spawn warrior: 2 villagers in the “spawn warrior” group and 12 wheat
- The Dragon can counterattack from the Cave, so large Cave populations early on are risky.

What’s new in this approach
- Fully adaptive, dynamic assault: The number of Warriors sent to the Cave each step (attack_batch) depends on Dragon HP and game progression. Early on, we send small waves; as the Dragon gets weaker, we allow larger waves. This aims to reduce risk from counterattacks while accelerating kill as HP drops.
- Wheat-driven growth remains: Farmers keep farming in the Village and we use wheat to spawn Farmers first (to sustain wheat production), then spawn Warriors if wheat allows.
- Farmers in the Cave retreat to the Village: Farmers stay in the Village to continue farming/spawning.

Key decision rules
- In assign_in_village:
  - Compute attack_batch based on dragon HP and step:
    - If there are no Warriors in the Village, batch = 0.
    - If dragon.hp <= 10: batch = min(3, available Warriors)
    - If dragon.hp <= 20: batch = min(2, available Warriors)
    - If dragon.hp <= 30: batch = min(2, available Warriors)
    - Else, ramp with step: step < 3 -> 1; step < 6 -> 2; otherwise -> 3 (bounded by available Warriors)
  - Move exactly attack_batch Warriors to the Cave.
  - Spawning using wheat:
    - spawns_farm = min(number_of_farmers_in_village // 2, wheat // 10)
    - Move 2*spawns_farm Farmers to the "spawn farmer" group
    - With remaining Farmers, spawn Warriors if wheat allows: spawns_warrior = min( remaining_farmers // 2, wheat_left // 12 )
    - Move 2*spawns_warrior Farmers to the "spawn warrior" group
    - Remaining Farmers stay in "farm" group
- In assign_in_cave:
  - Move all Warriors in the Cave to the "attack" group.
  - Move any Farmers in the Cave back to the "village" group.

Python implementation

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Group names
        farm_group = "farm"
        cave_group = "cave"
        spawn_farmer = "spawn farmer"
        spawn_warrior = "spawn warrior"

        # Separate Farmers and Warriors currently in the Village
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Fully adaptive assault: determine how many Warriors to send this step
        attack_batch = 0
        dragon_hp = getattr(environment.dragon, "hp", 0)

        if len(warriors) > 0:
            if dragon_hp <= 10:
                attack_batch = min(3, len(warriors))
            elif dragon_hp <= 20:
                attack_batch = min(2, len(warriors))
            elif dragon_hp <= 30:
                attack_batch = min(2, len(warriors))
            else:
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

        # Spawn Farmers first (2 Farmers per spawn, 10 wheat per spawn)
        spawns_farm = min(len(farmers) // 2, wheat // 10)
        for c in farmers[:2 * spawns_farm]:
            environment.assign_group(c, spawn_farmer)

        wheat_after_farm = wheat - spawns_farm * 10
        remaining_after_farm = farmers[2 * spawns_farm:]

        # Spawn Warriors with remaining Farmers (2 Farmers per spawn, 12 wheat per spawn)
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
            # Warriors in the Cave should attack
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, attack_group)
            else:
                # Farmers in the Cave retreat to the Village to farm/spawn
                environment.assign_group(c, village_group)
```