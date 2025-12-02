Reasoning and adaptation strategy (updated)

- Issue observed:
  - The previous implementation assigned Warriors to the cave, then attempted to reassign Farmers to farm or spawn groups. This caused some Farmers to be assigned more than once within assign_in_village, leading to test failures.
- Updated strategy:
  - In assign_in_village:
    - Move all Warriors to the cave (single assignment per Warrior to "cave").
    - Determine spawn allocations for Farmers in a single pass, so every Farmer gets assigned to exactly one group: either "spawn farmer", "spawn warrior", or "farm".
    - Spawning allocations are computed based on the current wheat in the Farm and the number of Farmers:
      - s_f = min(number_of_farmers // 2, wheat // 10)
      - remaining_farmers_for_w_w = number_of_farmers - 2 * s_f
      - s_w = min(remaining_farmers_for_w_w // 2, wheat // 12)
    - Then assign Farmers in a deterministic order:
      - First 2*s_f farmers → "spawn farmer"
      - Next 2*s_w farmers → "spawn warrior"
      - Remaining farmers → "farm"
  - In assign_in_cave:
    - Warriors go to "attack"; Farmers go to "village" (go back to the Village).
- Result: Each component in assign_in_village is assigned exactly once, no double-assignments. Warriors consistently end up in the cave, and Farmers either farm or participate in spawning, depending on wheat and counts.

Python implementation

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Divide villagers in the Village into:
        - farm: Stay in Village and farm
        - cave: Go to the Cave
        - spawn farmer: For every two villagers in this group and 10 wheat, spawn a Farmer
        - spawn warrior: For every two villagers in this group and 12 wheat, spawn a Warrior
        """
        # Separate villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # 1) Send all Warriors to the Cave (path to cave)
        for w in warriors:
            environment.assign_group(w, "cave")

        # 2) Farmers management in Village
        total_farmers = len(farmers)
        current_wheat = getattr(environment.farm, "wheat", 0)

        # 3) Determine spawning allocations based on current wheat and number of farmers
        s_f = min(total_farmers // 2, current_wheat // 10) if current_wheat >= 10 else 0
        remaining = total_farmers - 2 * s_f
        s_w = min(remaining // 2, current_wheat // 12) if current_wheat >= 12 else 0

        # 4) Assign farmers to exactly one group
        idx = 0
        # First 2*s_f to spawn farmer
        for _ in range(2 * s_f):
            if idx < total_farmers:
                environment.assign_group(farmers[idx], "spawn farmer")
                idx += 1
        # Next 2*s_w to spawn warrior
        for _ in range(2 * s_w):
            if idx < total_farmers:
                environment.assign_group(farmers[idx], "spawn warrior")
                idx += 1
        # Remaining farmers go to farming
        for j in range(idx, total_farmers):
            environment.assign_group(farmers[j], "farm")


    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Divide villagers in the Cave into:
        - attack: Attack the Dragon (Warriors should go here)
        - cave: Stay in the Cave (not used by our strategy)
        - village: Go to the Village (Farmers return to farming/spawning)
        """
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                # Farmers in the Cave should go back to the Village
                environment.assign_group(c, "village")
```