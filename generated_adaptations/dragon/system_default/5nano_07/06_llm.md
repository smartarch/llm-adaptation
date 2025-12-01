Reasoning and improved strategy

What changed and why
- The previous approach sent a larger batch of Warriors to the Cave early, which increased DPS but also raised the risk of the Dragon counterattacking and wiping out many villagers in the Cave.
- The new strategy adopts a phased assault: we send a small, step-dependent batch of Warriors to the Cave each turn. This reduces the per-turn risk from the Dragon’s attack while still ramping up DPS over time.
- Farmers remain the backbone of wheat production. We continue to farm with Farmers in the Village and use wheat to spawn new Farmers and Warriors, but we do so in a way that prioritizes sustaining wheat production early (spawn Farmers) and only then spawn Warriors if wheat allows.
- Any Farmers found in the Cave are moved back to the Village in the cave phase, ensuring Farmers stay in Village to farm/spawn rather than retreating to the Cave long-term.
- Spawn logic:
  - spawn farmer: for every two Farmers in the “spawn farmer” group and 10 wheat.
  - spawn warrior: for every two Farmers in the “spawn warrior” group and 12 wheat.
- This approach aims to achieve earlier, sustainable DPS growth while limiting the Dragon’s counterattack risk by keeping Cave populations smaller and rotating them.

Implementation notes
- In assign_in_village:
  - Determine a small, step-dependent attack_batch from Warriors in the Village to move to the Cave (cave group). The cave-to-attack transition happens in the next phase via assign_in_cave.
  - Use Wheat in environment.farm.wheat to decide spawning:
    - First allocate 2 Farmers to the “spawn farmer” group as many times as allowed by wheat (2 farmers per spawn, 10 wheat per spawn).
    - With leftover Farmers and Wheat, allocate 2 Farmers to the “spawn warrior” group (2 farmers per spawn, 12 wheat per spawn).
    - Remaining Farmers stay in the Farm group.
- In assign_in_cave:
  - All Warriors in the Cave move to the Attack group.
  - Any Farmers in the Cave move back to the Village.

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

        # Phased assault: send a small batch of Warriors to the Cave this step
        attack_batch = 0
        if len(warriors) > 0:
            if step <= 2:
                attack_batch = 1
            elif step <= 5:
                attack_batch = min(2, len(warriors))
            else:
                attack_batch = min(3, len(warriors))

        for i in range(attack_batch):
            environment.assign_group(warriors[i], cave_group)

        # Spawning logic using Wheat in the Farm
        wheat = getattr(environment.farm, "wheat", 0)

        # Farmers available to spawn (not already moved to cave this step)
        spawns_farm = min(len(farmers) // 2, wheat // 10)
        for c in farmers[:2 * spawns_farm]:
            environment.assign_group(c, spawn_farmer)

        wheat_after_farm = wheat - spawns_farm * 10
        remaining_after_farm = farmers[2 * spawns_farm:]

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