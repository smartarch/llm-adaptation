Strategy and reasoning (described before the code)

Goal-driven plan:
- Keep all Farmers in the Village and manage spawning to increase DPS and DPS diversity.
- Move all Warriors to the Cave to attack the Dragon; then in the Cave stage they should be assigned to the attack group to actually strike the Dragon.
- Use the spawn mechanisms to generate new Farmers and Warriors, ensuring the spawn conditions (2 villagers in a spawn group and enough wheat) are met. This helps ensure we have a steady influx of combatants while maintaining the rule that Farmers stay in the Village.
- Ensure at least one Dragon attack happens early (within the first 15 steps) by guaranteeing Warriors reach the Cave and join the attack soon after arrival. Since all Warriors are moved to the cave in village, and then assigned to attack in the cave, this will happen as soon as the cave step is processed.
- Keep most Warriors in the Cave to maximize the chance of killing the Dragon; by design, all Warriors are moved to the Cave in the village phase and then to the attack role in the cave phase.
- Spawn strategy: use available wheat to spawn new Farmers and Warriors. For every 2 farmers assigned to a spawn group, if there is enough wheat (10 for Farmer spawns, 12 for Warrior spawns), one new villager of the corresponding type is spawned. The code assigns 2 producers to each spawn group when possible, then assigns any remaining Farmers to farming (farm).

What changes I’m making:
- In assign_in_village:
  - Move all Warriors to the cave (via the "cave" group).
  - Allocate Farmers to spawn groups (spawn farmer and spawn warrior) based on current wheat, with the rest assigned to farming ("farm").
  - The exact number spawned depends on how many Farmers we can pair (in twos) and the wheat available.
- In assign_in_cave:
  - Move all Warriors to the "attack" group to actually attack the Dragon.
  - Move all Farmers to the "village" group to stay in the Village.
- The design ensures:
  - The Dragon is attacked at least once within the first 15 steps.
  - All Warriors are in the Cave (and then attacking).
  - Farmers stay in the Village (but may spawn additional villagers to boost future DPS).
  - A few new Farmers and Warriors are spawned to improve kill chances.
  - Most Warriors stay in the Cave (we assign all Warriors to attack in the cave stage).

Python code (SmartAdaptation class)

```py
import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Gather villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # 1) Move all Warriors to the cave (they will be in cave to be attacked)
        for w in warriors:
            if "cave" in group_ids:
                environment.assign_group(w, "cave")

        # 2) Spawn planning for Farmers (stay in Village)
        # Use available wheat to spawn new Farmers and Warriors.
        wheat = getattr(environment.farm, "wheat", 0)

        # Determine how many farmer-spawns we can perform (2 farmers per spawn, needs 10 wheat)
        spawn_farmer_count = 0
        if len(farmers) >= 2 and wheat >= 10:
            spawn_farmer_count = min(len(farmers) // 2, wheat // 10)

        # Assign first 2*spawn_farmer_count farmers to "spawn farmer"
        idx = 0
        for i in range(2 * spawn_farmer_count):
            if idx < len(farmers) and "spawn farmer" in group_ids:
                environment.assign_group(farmers[idx], "spawn farmer")
                idx += 1
        wheat -= spawn_farmer_count * 10  # Wheat consumed by farmer spawns

        # 3) Now consider spawning Warriors (2 farmers per spawn, needs 12 wheat)
        remaining_farmers = farmers[idx:]
        spawn_warrior_count = 0
        if len(remaining_farmers) >= 2 and wheat >= 12:
            spawn_warrior_count = min(len(remaining_farmers) // 2, wheat // 12)

        # Assign next 2*spawn_warrior_count farmers to "spawn warrior"
        for i in range(2 * spawn_warrior_count):
            fi = idx + i
            if fi < len(farmers) and "spawn warrior" in group_ids:
                environment.assign_group(farmers[fi], "spawn warrior")
        idx += 2 * spawn_warrior_count  # advance index

        # 4) Remaining farmers go to farming in Village
        for j in range(idx, len(farmers)):
            if "farm" in group_ids:
                environment.assign_group(farmers[j], "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In Cave:
        # - Warriors should attack the Dragon
        # - Farmers should stay in Village
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                if "attack" in group_ids:
                    environment.assign_group(c, "attack")
                else:
                    # Fallback: stay in Cave if no explicit attack group
                    if "cave" in group_ids:
                        environment.assign_group(c, "cave")
            else:
                # Farmers stay in Village
                if "village" in group_ids:
                    environment.assign_group(c, "village")
```