Reasoning and updated adaptation strategy

Issue identified
- The previous implementation assigned some villagers to multiple groups within assign_in_village. Specifically, it first assigned all farmers to "farm" and then re-assigned some of them to "spawn farmer" or "spawn warrior" in the same function. This caused some components to be assigned more than once, which violated the test expectations.

Updated strategy
- Do a single, deterministic pass to decide the final group for every villager in the village.
- Rules:
  - All Warriors must end up in the cave (group "cave") in the village phase.
  - All Farmers should stay in the Village by default (group "farm").
  - Spawn groups are optional and are decided in a single pass based on Wheat and available Farmers:
    - If at least 4 Farmers and Wheat >= 20: assign two to "spawn farmer" and two to "spawn warrior" (uses up to four Farmers; others stay in "farm").
    - Else if at least 2 Farmers and Wheat >= 12: assign two Farmers to "spawn warrior".
    - Else if at least 2 Farmers and Wheat >= 10: assign two Farmers to "spawn farmer".
  - Each component is assigned exactly once.
- In assign_in_cave, keep a single pass to assign groups:
  - Warriors go to "attack".
  - Farmers go to "village".
- This approach satisfies:
  - All warriors go to cave and attack.
  - Farmers stay in village by default (with spawn options as a single assignment).
  - Spawning occurs deterministically when resources allow.
  - No repeated assignments in a single step.

Updated Python code

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Assign villagers in the Village to:
        - farm: Farmers stay and farm
        - cave: Go to the Cave
        - spawn farmer: For every two villagers in this group and 10 wheat, a new Farmer is spawned.
        - spawn warrior: For every two villagers in this group and 12 wheat, a new Warrior is spawned.
        """
        # Classify villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Final assignment mapping (component -> group)
        final_group = {}

        # Base assignments
        for w in warriors:
            final_group[w] = "cave"   # Warriors go to the Cave
        for f in farmers:
            final_group[f] = "farm"   # Farmers stay in the Village by default

        # Wheat available in the Farm
        wheat = 0
        if hasattr(environment, "farm") and getattr(environment.farm, "wheat", None) is not None:
            wheat = environment.farm.wheat

        # Spawn decisions (single-pass, one assignment per component)
        if len(farmers) >= 4 and wheat >= 20:
            final_group[farmers[0]] = "spawn farmer"
            final_group[farmers[1]] = "spawn farmer"
            final_group[farmers[2]] = "spawn warrior"
            final_group[farmers[3]] = "spawn warrior"
        elif len(farmers) >= 2 and wheat >= 12:
            final_group[farmers[0]] = "spawn warrior"
            final_group[farmers[1]] = "spawn warrior"
        elif len(farmers) >= 2 and wheat >= 10:
            final_group[farmers[0]] = "spawn farmer"
            final_group[farmers[1]] = "spawn farmer"

        # Apply the final assignments (each component assigned exactly once)
        for comp, gid in final_group.items():
            environment.assign_group(comp, gid)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Divide villagers in the Cave into:
        - attack: Warriors attack the Dragon
        - cave: Stay in the Cave
        - village: Go to the Village
        """
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```