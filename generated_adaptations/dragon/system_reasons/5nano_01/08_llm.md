Reasoning and new adaptation approach:
- Goal adherence remains: all Warriors should go to the Cave and attack; Farmers stay in the Village (but can be used to spawn more villagers).
- New strategy: per-step incremental growth
  - Move all existing Warriors to the Cave immediately so they can contribute to the very next attack.
  - Spawn at most one batch of Farmers per step (if there are at least 2 Farmers and at least 10 wheat). Each batch yields 2 new Farmers.
  - If there is still wheat after spawning Farmers, spawn at most one batch of Warriors (if there are enough Farmers left to support the spawn and at least 12 wheat is available). Each batch yields 2 new Warriors.
  - This creates a steady growth of both Farmers (to sustain wheat) and Warriors (to increase DPS) across steps, aiming to increase DPS early enough to kill the Dragon faster, without starving wheat for early farming too aggressively.
- Cave behavior remains the same: Warriors attack, Farmers return to Village.

Code (Python) implementing the improved strategy:

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate villagers by role
        farmers = [c for c in components if getattr(c, "role", "") == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", "") == "Warrior"]

        # Strategy: move all existing warriors to the cave to prepare for attack
        for w in warriors:
            environment.assign_group(w, "cave")

        # Wheat available for spawning decisions
        wheat = getattr(environment.farm, "wheat", 0)
        n_farmers = len(farmers)

        # Spawn up to one batch of farmers this step (2 farmers, cost 10 wheat)
        spawns_farm = 0
        if n_farmers >= 2 and wheat >= 10:
            spawns_farm = 1

        wheat_after_farm = wheat - spawns_farm * 10
        remaining_farmers_after_farm = n_farmers - spawns_farm * 2

        # Spawn up to one batch of warriors this step (2 warriors, cost 12 wheat)
        spawns_war = 0
        if remaining_farmers_after_farm >= 2 and wheat_after_farm >= 12:
            spawns_war = 1

        idx = 0
        # Assign farmers destined to spawn as farmers
        for _ in range(spawns_farm * 2):
            if idx < len(farmers):
                environment.assign_group(farmers[idx], "spawn farmer")
                idx += 1

        # Assign farmers destined to spawn as warriors
        for _ in range(spawns_war * 2):
            if idx < len(farmers):
                environment.assign_group(farmers[idx], "spawn warrior")
                idx += 1

        # Remaining farmers go to farming (stay in village)
        while idx < len(farmers):
            environment.assign_group(farmers[idx], "farm")
            idx += 1

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the cave:
        # - Warriors attack the Dragon
        # - Farmers return to the Village (stay in village by default)
        for c in components:
            if getattr(c, "role", "") == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```