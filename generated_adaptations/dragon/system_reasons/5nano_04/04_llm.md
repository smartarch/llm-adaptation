Reasoning and updated adaptation strategy

Issue observed
- The previous implementation assigned the same farmer multiple times in assign_in_village (first to farm, then possibly to spawn groups). This caused some components to be assigned more than once within a single call to assign_in_village, which tests flagged.

Strategy improvement
- Compute a single, final target group for each villager in assign_in_village, avoiding multiple passes that re-assign the same component.
- Determine spawn opportunities sequentially to reflect wheat consumption:
  - Start with all Farmers assigned to "farm".
  - If there are at least two Farmers and wheat >= 10, designate two Farmers for "spawn farmer" and deduct 10 wheat.
  - Re-evaluate remaining Farmers; if at least two remain and the remaining wheat >= 12, designate two for "spawn warrior" and deduct 12 wheat.
- All Warriors should end up in the Cave (group "cave") in the village phase, since they must move to the Cave to attack.
- After computing final_group for all villagers, assign each component exactly once.

This preserves the requirements:
- No repeated assignments in assign_in_village.
- All Warriors go to cave; all Farmers stay in the Village or participate in spawning.
- Spawn groups are used conditionally based on available wheat.
- The code assigns every component to exactly one valid group.

Code (Python)

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Groups:
        # - "farm": stay in Village and farm
        # - "cave": go to the Cave
        # - "spawn farmer": spawn new Farmer (needs 2 villagers + 10 wheat)
        # - "spawn warrior": spawn new Warrior (needs 2 villagers + 12 wheat)

        # Gather villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        final_group = {}

        # Default: all farmers to farming in village
        for f in farmers:
            final_group[f] = "farm"

        # Wheat available on the Farm
        farm = getattr(environment, "farm", None)
        wheat = getattr(farm, "wheat", 0) if farm is not None else 0

        # Spawn farmer: if at least 2 farmers and wheat >= 10
        if len(farmers) >= 2 and wheat >= 10:
            chosen = farmers[:2]
            for c in chosen:
                final_group[c] = "spawn farmer"
            wheat -= 10

        # Remaining farmers eligible for spawning warriors
        remaining = [f for f in farmers if final_group.get(f) != "spawn farmer"]

        # Spawn warrior: if at least 2 remaining and wheat >= 12
        if len(remaining) >= 2 and wheat >= 12:
            chosen2 = remaining[:2]
            for c in chosen2:
                final_group[c] = "spawn warrior"
            wheat -= 12

        # Warriors go to cave
        for w in warriors:
            final_group[w] = "cave"

        # Ensure every component is assigned exactly once
        for c in components:
            grp = final_group.get(c, "farm")
            environment.assign_group(c, grp)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In Cave:
        # - Warriors attack the Dragon
        # - Farmers go back to Village (stay in Village)
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```