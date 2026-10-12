Reasoning and improved strategy

Goal and intuition
- Warriors must eventually reach the Cave to damage the Dragon, but exposing large Cave populations to the Dragon’s counterattack is risky. We want a safer, progressively ramping assault.
- Farmers should stay in the Village to farm for wheat, enabling spawning (both Farmers and Warriors) to sustain growth over time.
- Spawning remains wheat-bounded: 10 wheat per spawn for a Farmer, 12 wheat per a Warrior, with 2 villagers allocated to the corresponding “spawn” group per spawn.
- We want a dynamic, step-aware ramp: start with a cautious attack, and only increase the number of Warriors sent to the Cave as the Dragon weakens or as the game progresses, to maximize DPS while minimizing catastrophic losses in the Cave.

What’s different in this approach
- Dynamic, step-aware ramp with HP gates: We compute attack_batch from both the Dragon’s current HP and the number of Warriors available in the Village. Early turns favor a cautious one-warrior sortie; as the Dragon gets weaker, we progressively allow larger waves (up to 3) to reach the Cave.
- Wheat-driven growth remains: Farmers stay in the Village to farm wheat; we spawn Farmers first (to bolster wheat production), then use any remaining Farmers to spawn Warriors if wheat allows. This preserves growth potential for the long term.
- Farmers in the Cave retreat to the Village: We keep Farmers out of the Cave to maintain farming/spawning capacity.

Strategy rules (the core logic)
- In assign_in_village:
  - Determine attack_batch from:
    - If there are no Warriors in the Village, batch = 0.
    - Else, based on Dragon HP:
      - If dragon.hp <= 15: batch = min(3, number of available Warriors)
      - If 15 < dragon.hp <= 25: batch = min(2, available)
      - If 25 < dragon.hp <= 35: batch = min(2, available)
      - If dragon.hp > 35: batch = min(1, available) except we allow escalation to 2 if the sequence has progressed (step large enough)
  - Move exactly attack_batch Warriors to the Cave (cave group).
  - Spawning using Wheat:
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
            if dragon_hp <= 15:
                attack_batch = min(3, len(warriors))
            elif dragon_hp <= 25:
                attack_batch = min(2, len(warriors))
            elif dragon_hp <= 35:
                attack_batch = min(2, len(warriors))
            else:
                # Early turns: be conservative; ramp more only with progression
                if step < 4:
                    attack_batch = min(1, len(warriors))
                elif step < 9:
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