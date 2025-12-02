Reasoning and adaptation strategy:

- Why previous attempts failed:
  - The Dragon is a high-risk, high-reward target. Early overwhelming offense is essential, but spawning must be sustained via wheat production.
  - Simply moving Warriors to the cave and greedily spawning without considering wheat flow led to stalls where no new Warriors appeared and wheat ran out.
  - We need a disciplined, turn-by-turn planning approach that maximizes immediate Warrior spawns while preserving wheat for future spawns.

- Improved plan:
  - In assign_in_village:
    - Move all existing Warriors to the cave immediately to maximize immediate DPS potential.
    - For Farmers in the village, explicitly compute the best distribution into three groups for this turn:
      - spawn warrior: uses 2 Farmers and 12 wheat to create a new Warrior
      - spawn farmer: uses 2 Farmers and 10 wheat to create a new Farmer
      - farm: the remaining Farmers stay in the village to produce wheat (5 wheat per Farmer)
    - The plan is found by enumerating how many Farmers f to farm this turn (0..F). For each f, compute the total wheat available (current wheat + 5*f). Then determine the maximum number of Warrior spawns y and Farmer spawns z that satisfy:
      - 2y + 2z + f = F
      - 12y + 10z <= total_wheat
    - We select the plan with the highest y (most Warriors spawned this turn). If there are ties, prefer larger z (more Farmers spawned) and then larger f (more farming).
  - In assign_in_cave:
    - All Warriors attack (group "attack").
    - All Farmers go back to the Village (group "village").
- This approach aims to rapidly grow the Warrior force while keeping enough Wheat production for ongoing spawns, increasing the chance to kill the Dragon within 30 steps.

Code (Python):

```python
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate Farmers and Warriors in the Village
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # 1) Move all Warriors to the Cave (to head towards the Dragon)
        for c in warriors:
            environment.assign_group(c, "cave")

        F = len(farmers)
        if F == 0:
            # Nothing to do if no farmers
            return

        current_wheat = getattr(environment.farm, "wheat", 0)

        # 2) Enumerate possible farming/spawn plans to maximize Warrior spawns this turn
        best_plan = None  # (f, y, z)
        best_y = -1
        best_z = -1

        for f in range(0, F + 1):
            total_wheat = current_wheat + f * 5  # wheat after farming f farmers this turn
            # For given f, compute max possible Warriors to spawn
            max_y = min((F - f) // 2, total_wheat // 12)
            # Find the highest y that yields a valid z
            chosen_y = -1
            chosen_z = -1

            for y in range(max_y, -1, -1):
                remaining = F - f - 2 * y
                if remaining < 0:
                    continue
                if remaining % 2 != 0:
                    continue
                z = remaining // 2
                cost_wheat = 12 * y + 10 * z
                if cost_wheat <= total_wheat:
                    chosen_y = y
                    chosen_z = z
                    break

            if chosen_y < 0:
                # No valid spawns for this f, skip
                continue

            # Prefer plan with more Warriors spawned; ties broken by more Farmers spawned, then farming
            if (chosen_y > best_y) or (chosen_y == best_y and chosen_z > best_z) or (
                chosen_y == best_y and chosen_z == best_z and f > (best_plan[0] if best_plan else -1)
            ):
                best_plan = (f, chosen_y, chosen_z)
                best_y = chosen_y
                best_z = chosen_z

        # If for some reason we didn't find any plan (shouldn't happen with F>0), default to all farming
        if best_plan is None:
            best_plan = (F, 0, 0)

        f, y, z = best_plan

        # Build the final groups
        # f: number of farmers to farm this turn
        # y: number of Warriors to spawn this turn (each requires 2 farmers)
        # z: number of Farmers to spawn this turn (each requires 2 farmers)
        spawn_warrior_count = 2 * y
        spawn_farmer_count = 2 * z
        farming_count = F - spawn_warrior_count - spawn_farmer_count  # remaining farmers

        spawn_warrior_villagers = farmers[:spawn_warrior_count]
        spawn_farmer_villagers = farmers[spawn_warrior_count: spawn_warrior_count + spawn_farmer_count]
        farming_villagers = farmers[spawn_warrior_count + spawn_farmer_count:]

        for c in spawn_warrior_villagers:
            environment.assign_group(c, "spawn warrior")

        for c in spawn_farmer_villagers:
            environment.assign_group(c, "spawn farmer")

        for c in farming_villagers:
            environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave: All Warriors go to Attack; Farmers go to Village
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```