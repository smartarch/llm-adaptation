Reasoning and improved strategy

Goal recap
- Warriors must eventually reach the Cave and attack the Dragon.
- Farmers should stay in the Village to farm and enable spawning (both Farmers and Warriors).
- We still spawn using wheat in the Farm, with rules:
  - spawn farmer: 2 villagers in the “spawn farmer” group and 10 wheat
  - spawn warrior: 2 villagers in the “spawn warrior” group and 12 wheat
- The Dragon counterattacks from the Cave with non-negligible risk, so large Cave populations early on are dangerous.

Key idea of the new approach
- Dynamic, phased assault: Instead of a fixed ramp, we adapt the number of Warriors sent to the Cave based on game state.
  - Use dragon hp to regulate aggression: when the Dragon is strong, send smaller batches to limit casualties; as HP drops, increase the batch size to accelerate kill.
  - Combine with step-based progression to gradually ramp up DPS while keeping Cave populations manageable.
- Wheat-driven growth remains: Farmers in the Village farm to produce wheat; use wheat first to spawn Farmers, then Warriors, ensuring long-term growth even while pressing the attack.
- Farmers in the Cave retreat to the Village each cave phase to keep farming/spawning capability.

Strategy outline
- In assign_in_village:
  - Compute attack_batch with a dynamic rule:
    - If there are no Warriors in village, 0.
    - If dragon.hp <= 15: attack_batch = min(3, available Warriors)
    - Else if dragon.hp <= 25: attack_batch = min(2, available Warriors)
    - Else, use a step-based ramp:
      - step < 4: attack_batch = 1
      - 4 <= step < 9: attack_batch = min(2, available)
      - step >= 9: attack_batch = min(3, available)
  - Move exactly attack_batch Warriors to the Cave (cave group).
  - Use wheat to spawn Farmers first (2 Farmers per spawn, 10 wheat per spawn).
  - With remaining Farmers, spawn Warriors if wheat allows (2 Farmers per spawn, 12 wheat per spawn).
  - Remaining Farmers stay in Farm.

- In assign_in_cave:
  - Move all Warriors in the Cave to the Attack group.
  - Move any Farmers in the Cave back to the Village.

This approach aims to:
- Achieve faster kill when the Dragon is near defeat by ramping up the Cave attackers.
- Limit catastrophic deaths by keeping initial cave populations small and increasing only as the Dragon weakens.
- Maintain wheat production to sustain growth via spawning.

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

        # Dynamic phased assault: determine how many Warriors to send this step
        attack_batch = 0
        dragon_hp = getattr(environment.dragon, "hp", 0)

        if len(warriors) > 0:
            if dragon_hp <= 15:
                attack_batch = min(3, len(warriors))
            elif dragon_hp <= 25:
                attack_batch = min(2, len(warriors))
            else:
                if step < 4:
                    attack_batch = 1
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