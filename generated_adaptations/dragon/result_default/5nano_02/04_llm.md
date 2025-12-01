Reasoning and strategy update:
- Goal: Win in as few turns as possible by balancing wheat farming, spawning, and damage output.
- Key observations:
  - Warriors do high damage (3 per attack) but each is vulnerable in the Dragon’s Cave. We should keep numbers in Cave moderate to minimize losses.
  - Farmers are essential for wheat production (5 wheat per farming action). Wheat is the resource to spawn new villagers.
  - Spawning can quickly grow our army, but it costs wheat and requires two villagers in a spawn group.
  - All Warriors must eventually go to the Cave to attack; Farmers stay in the Village to farm or spawn.
- Improved strategy:
  - In the Village:
    - Spawn as many farmers as possible each step given available wheat, because each new farmer increases future wheat production.
    - If there is spare wheat and enough farmers left, spawn some warriors to increase DPS, but only from farmers (to avoid depleting the farmer pool too aggressively). The newly spawned warriors will come from villagers in spawn warrior group and will join the Cave in the next steps.
    - Keep a healthy base of farmers in the Village to sustain wheat production; avoid over-committing all villagers to spawning during early steps.
  - In the Cave:
    - All existing Warriors go to attack the Dragon.
    - Farmers in the Cave return to the Village (they should never stay in the Cave long-term).
- This adaptive approach aims to grow wheat production first, then ramp up DPS with additional warriors, all while controlling risk by not stacking too many villagers in the Cave at once.

Code (Python):
```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        In the Village:
        - Spawn farmers as much as possible given 10 wheat per farmer and 2 villagers per spawn.
        - If wheat remains and there are at least 2 farmers left after spawning farmers, spawn warriors
          using 12 wheat per warrior (requires 2 villagers in the "spawn warrior" group).
        - Remaining farmers go to the 'farm' group to continue producing wheat.
        - Warriors are not kept in the Village; they should go to the Cave to attack.
        """
        # Separate villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        wheat = getattr(environment.farm, "wheat", 0)

        # 1) Spawn farmers as much as possible
        max_farm_spawns = min(len(farmers) // 2, wheat // 10)
        spawn_farmers = farmers[:2 * max_farm_spawns]
        remaining_farmers = farmers[2 * max_farm_spawns:]

        # Update wheat after farmer spawns
        wheat_after_farm = wheat - max_farm_spawns * 10

        # 2) Spawn warriors if possible with remaining farmers and wheat
        spawn_warriors = []
        if len(remaining_farmers) >= 2 and wheat_after_farm >= 12:
            max_war_spawns = min(len(remaining_farmers) // 2, wheat_after_farm // 12)
            spawn_warriors = remaining_farmers[:2 * max_war_spawns]
            remaining_farmers = remaining_farmers[2 * max_war_spawns:]
            # wheat_after_war would be wheat_after_farm - max_war_spawns*12
            # but we don't need to track beyond this step for grouping

        # Assign groups
        for c in spawn_farmers:
            environment.assign_group(c, "spawn farmer")
        for c in remaining_farmers:
            environment.assign_group(c, "farm")
        for c in spawn_warriors:
            environment.assign_group(c, "spawn warrior")

        # All existing Warriors go to the Cave
        for c in warriors:
            environment.assign_group(c, "cave")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        In the Cave:
        - Warriors attack the Dragon.
        - Farmers go back to the Village.
        - (No Farmers stay in Cave long-term by policy.)
        """
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```