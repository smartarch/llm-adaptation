Reasoning and improved strategy

Goal and constraints
- Warriors must eventually reach the Cave to attack the Dragon.
- Farmers stay in the Village to farm and enable spawning (both Farmers and Warriors).
- Spawning remains wheat-bounded:
  - spawn farmer: 2 villagers in the “spawn farmer” group and 10 wheat
  - spawn warrior: 2 villagers in the “spawn warrior” group and 12 wheat
- The Dragon can counterattack from the Cave, so large Cave populations early on are risky. We want a dynamic, phase-safe ramp that increasingly pressures the Dragon as HP drops.

What’s new in this approach
- Fully adaptive, dynamic assault: The number of Warriors sent to the Cave each step (attack_batch) depends on Dragon HP and game progression, but with a more conservative early ramp and a smarter late ramp.
  - Early turns: small waves to reduce risk.
  - As the Dragon weakens (lower HP) or with more game progression, ramp up to larger waves to finish sooner.
- Wheat-driven growth remains: Farmers stay in the Village to farm wheat; we spawn Farmers first (to bolster wheat production), then use any remaining Farmers to spawn Warriors if wheat allows. This preserves growth potential for the long term.
- Farmers in the Cave retreat to the Village: Farmers are kept in the Village to maintain farming/spawning capacity.

Strategy rules (core logic)
- In assign_in_village:
  - Determine attack_batch from Dragon HP and step:
    - If there are no Warriors in the Village: 0
    - If dragon.hp <= 8: attack_batch = min(3, available Warriors)
    - If dragon.hp <= 15: attack_batch = min(3, available)
    - If dragon.hp <= 25: attack_batch = min(2, available)
    - If dragon.hp <= 35: attack_batch = min(2, available)
    - Else: ramp by step (conservative early): step < 2 -> 1; step < 6 -> 2; otherwise -> 3
  - Move exactly attack_batch Warriors to the Cave (cave group).
  - Spawning using wheat:
    - spawns_farm = min(number_of_farmers_in_village // 2, wheat // 10)
    - Move 2*spawns_farm Farmers to the "spawn farmer" group
    - With the remaining Farmers, spawn Warriors if wheat allows: spawns_warrior = min( remaining_farmers // 2, wheat_after_farm // 12 )
    - Move 2*spawns_warrior Farmers to the "spawn warrior" group
    - Remaining Farmers stay in the Farm group
- In assign_in_cave:
  - Move all Warriors in the Cave to the Attack group.
  - Move any Farmers in the Cave back to the Village.

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

        # Dynamic, cautious to aggressive ramp: determine how many Warriors to send this step
        attack_batch = 0
        dragon_hp = getattr(environment.dragon, "hp", 0)

        if len(warriors) > 0:
            if dragon_hp <= 8:
                attack_batch = min(3, len(warriors))
            elif dragon_hp <= 15:
                attack_batch = min(3, len(warriors))
            elif dragon_hp <= 25:
                attack_batch = min(2, len(warriors))
            elif dragon_hp <= 35:
                attack_batch = min(2, len(warriors))
            else:
                # Early turns: be conservative; ramp more only with progression
                if step < 2:
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