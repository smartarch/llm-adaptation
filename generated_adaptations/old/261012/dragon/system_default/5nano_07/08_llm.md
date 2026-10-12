Reasoning and improved strategy

Goal and constraints recap
- We still require Warriors to go to the Cave and attack, and Farmers to stay in the Village to farm and enable spawning.
- The Dragon punishes the Cave population with potential mass casualties each turn. Therefore, we want a safer ramp-up of Cave attackers rather than sending all Warriors at once.
- Spawning continues to rely on pairs of villagers in a spawn group plus wheat (10 for farmers, 12 for warriors).

What’s new in this approach
- Phased, dynamic assault: We move a small batch of Warriors to the Cave each step, with the batch size gradually increasing as the game progresses. This reduces the risk of catastrophic Dragon counterattacks wiping out large Cave populations early on, while still building up DPS over time.
- Wheat-driven growth remains: Farmers continue farming in the Village and we allocate wheat to spawn new Farmers first (to sustain long-term growth), followed by spawning Warriors if wheat allows.
- Farmers in the Cave retreat to the Village: This ensures Farmers remain in Village to farm/spawn.

Key decision rules
- In assign_in_village:
  - Determine a phase-based attack_batch from Warriors in the Village:
    - step < 5 -> attack_batch = 1
    - 5 <= step < 12 -> attack_batch = 2 (if available)
    - step >= 12 -> attack_batch = min(3, available Warriors)
  - Move exactly attack_batch Warriors to the Cave this step.
  - Spawning:
    - spawns_farm = min(number_of_farmers_in_village // 2, wheat // 10)
    - Move 2*spawns_farm Farmers to the "spawn farmer" group.
    - Remaining farmers can spawn warriors if wheat allows: spawns_warrior = min( remaining_farmers // 2, wheat_after_farm // 12 )
    - Move 2*spawns_warrior Farmers to the "spawn warrior" group.
    - All other Farmers stay in the "farm" group.

- In assign_in_cave:
  - Move all Warriors in the Cave to the "attack" group.
  - Move any Farmers in the Cave back to the "village" group.

This approach aims for faster early DPS than a purely very-late ramp, while keeping a low enough Cave population early to mitigate Dragon counterattacks.

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

        # Phased assault: determine how many Warriors to send this step
        attack_batch = 0
        if len(warriors) > 0:
            if step < 5:
                attack_batch = 1
            elif step < 12:
                attack_batch = min(2, len(warriors))
            else:
                attack_batch = min(3, len(warriors))

        for i in range(attack_batch):
            environment.assign_group(warriors[i], cave_group)

        # Spawning logic using Wheat in the Farm
        wheat = getattr(environment.farm, "wheat", 0)

        # Farmers available to spawn (excluding those just moved to cave this step)
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