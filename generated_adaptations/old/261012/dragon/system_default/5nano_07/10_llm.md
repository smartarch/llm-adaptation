Reasoning and improved strategy

Goal refinements
- Warriors must eventually reach the Cave and attack, but we want to avoid dumping a large cave population into the Dragon’s counterattack all at once.
- Farmers should keep farming to grow wheat, which enables spawning new villagers. Spawning order matters: generate Farmers early (to sustain wheat production) and then spawn Warriors if wheat allows.
- We want a staged, wave-like assault: small, escalating batches of Warriors enter the Cave over time, while Farmers continuously farm and spawn as wheat allows. Any Farmers found in the Cave should retreat to the Village.

Key ideas
- Phased attack: send 1 Warrior to the Cave for early turns, then 2, then 3 as the game progresses, capped by available Warriors. This reduces immediate risk and still accelerates DPS as the Dragon is whittled down.
- Wheat-driven spawning: allocate wheat to spawn Farmers first (2 Farmers per spawn, 10 wheat per spawn), then use remaining Farmers and wheat to spawn Warriors (2 Farmers per spawn, 12 wheat per spawn). This maintains wheat production and enables growth.
- Farmers in Cave always return to Village: keep Farmers in the Village for farming/spawning.

Implementation outline
- In assign_in_village:
  - Compute a phased attack_batch based on step (gradual ramp).
  - Move attack_batch Warriors to the Cave.
  - Use wheat to spawn as many Farmers as possible (spawn_farmer).
  - With remaining Farmers, spawn Warriors if wheat allows (spawn_warrior).
  - Remaining Farmers stay in Farm group.
- In assign_in_cave:
  - Move Warriors in the Cave to the Attack group.
  - Move Farmers in the Cave back to the Village (Farm/Spawn next round).

Code
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

        # Phased assault: determine how many Warriors to send this step (gradual ramp)
        attack_batch = 0
        if len(warriors) > 0:
            if step < 4:
                attack_batch = 1
            elif step < 9:
                attack_batch = min(2, len(warriors))
            elif step < 16:
                attack_batch = min(3, len(warriors))
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