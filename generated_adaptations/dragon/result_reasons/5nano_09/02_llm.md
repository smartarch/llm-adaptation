Reasoning and adaptation strategy:

Goal alignment:
- Kill the Dragon as fast as possible.
- Warriors are the primary damage dealers; all Warriors should move to the Cave and attack the Dragon.
- Farmers stay in the Village to farm and to enable spawning of more villagers (both Farmers and Warriors) using the spawn mechanics.
- We want to ensure an early attack (within the first 15 steps) and a steady DPS by keeping a significant number of Warriors in the Cave attacking.
- We also want to build a small but ongoing pipeline of new Farmers and Warriors by using the spawn groups, driven by Wheat in the Farm.

Strategy overview:
- In assign_in_village:
  - Move all Warriors to the Cave (to eventually attack the Dragon).
  - Keep Farmers in the Village by default in the "farm" group.
  - Use a controlled spawning policy:
    - If there is enough Wheat (10 per Farmer-spawn) and enough Farmers to spare, assign some Farmers to "spawn farmer" to create new Farmers.
    - If Wheat is still available after Farmer spawns (and there are spare Farmers), assign some Farmers to "spawn warrior" to create new Warriors.
    - We cap the spawns to avoid runaway growth (e.g., at most 2 spawns per type per step) and rely on Wheat and farmer count to govern feasibility.
  - This ensures a rolling production of new villagers while keeping all Farmers in the Village and all Warriors in the Cave.

- In assign_in_cave:
  - Move all Warriors to the "attack" group so they actively attack the Dragon.
  - Move any Farmers in the Cave back to the Village via the "village" group (to comply with the rule that Farmers stay in the Village).

This strategy guarantees:
- All Warriors go to the Cave and attack.
- Farmers stay in the Village, with a spawned-wheat-driven mechanism to produce additional Farmers and Warriors.
- The Dragon is attacked early (by at least one Warrior in cave within the first 15 steps) and continues to receive DPS as Warriors are in the Cave/Attack group.
- A steady pipeline of extra Farmers and Warriors increases the chance of killing the Dragon within the 30-step window.

Python implementation:

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate farmers and warriors in the village
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # 1) All Warriors go to the Cave (to eventually attack)
        for w in warriors:
            environment.assign_group(w, "cave")

        # 2) Farmers stay in Village by default (to farm or spawn)
        # We'll decide on spawns to introduce new villagers using wheat.

        # Spawning policy (driven by wheat and available farmers)
        total_farmers = len(farmers)
        if total_farmers == 0:
            # No Farmers to manage spawning; nothing more to do
            return

        # Determine how many Farmer-spawns we can attempt this step
        wheat = getattr(environment.farm, "wheat", 0)

        # Max possible farmer spawns this step given wheat and available farmers (2 farmers per spawn)
        max_farm_spawns = min(total_farmers // 2, wheat // 10)
        to_spawn_farmers = min(max_farm_spawns, 2)  # cap to avoid over-spawning

        idx = 0
        # Assign 2*to_spawn_farmers farmers to "spawn farmer"
        for _ in range(to_spawn_farmers * 2):
            if idx >= total_farmers:
                break
            c = farmers[idx]
            environment.assign_group(c, "spawn farmer")
            idx += 1

        remaining_farmers_after_farm_spawns = total_farmers - idx

        # Remaining wheat after farm spawns
        wheat_after_farm_spawns = wheat - (to_spawn_farmers * 10)

        # Determine how many Warrior-spawns we can attempt with remaining farmers
        max_available_for_warrior_spawns = remaining_farmers_after_farm_spawns // 2
        to_spawn_warriors = min(max_available_for_warrior_spawns, wheat_after_farm_spawns // 12)
        to_spawn_warriors = min(to_spawn_warriors, 2)  # cap to avoid excessive spawns

        # Assign 2*to_spawn_warriors farmers to "spawn warrior"
        for _ in range(to_spawn_warriors * 2):
            if idx >= total_farmers:
                break
            c = farmers[idx]
            environment.assign_group(c, "spawn warrior")
            idx += 1

        # The rest of the farmers go to "farm"
        while idx < total_farmers:
            c = farmers[idx]
            environment.assign_group(c, "farm")
            idx += 1

        # Note: If there are no farmers left to spawn, remaining villagers (farmers)
        # are already assigned to "farm" by the above loop cycle.

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the cave: Warriors should attack; Farmers should go back to Village
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                # Farmers should stay in Village
                environment.assign_group(c, "village")
```