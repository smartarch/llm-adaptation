Reasoning and strategy (step-by-step)

- Objective recap: Kill the Dragon as fast as possible. Warriors are best at dealing damage; Farmers are needed to generate wheat to fund spawning of new villagers (both Farmers and Warriors). Spawning requires two villagers assigned to a spawn group plus a wheat threshold (10 for farmers, 12 for warriors).
- Roles and movement:
  - Warriors should end up in the Cave and then attack the Dragon.
  - Farmers should stay in the Village to farm or spawn new villagers.
- Spawn mechanics:
  - In the Village, we can designate some Farmers to the spawn groups:
    - spawn farmer: for every 2 farmers assigned to this group and 10 wheat, a new Farmer is spawned.
    - spawn warrior: for every 2 farmers assigned to this group and 12 wheat, a new Warrior is spawned.
  - To maximize early gains, we should allocate as many Farmers as possible to spawning, given the available wheat and the number of Farmers.
  - The remaining Farmers should stay in the Village and farm (produce wheat) to support further spawns.
  - All Warriors should head to the Cave (to eventually Attack).
- Implementation plan:
  - assign_in_village:
    - Separate Farmers and Warriors from the Village components.
    - Compute how many spawn pairs we can form:
      - Try all possibilities for f spawn-farmer pairs and w spawn-warrior pairs, subject to 2f + 2w <= number_of_farmers
        and 10f + 12w <= available_wheat.
      - Choose the (f, w) that maximizes f + w (total spawned villagers) to maximize future DPS.
    - Assign:
      - First 2f Farmers to "spawn farmer"
      - Next 2w Farmers to "spawn warrior"
      - Remaining Farmers to "farm"
      - All Warriors to "cave" (to go to cave)
  - assign_in_cave:
    - All Warriors assigned to "attack" (to attack the Dragon)
    - All Farmers assigned to "village" (to go back to the Village)
- This strategy ensures Warriors promptly contribute damage, Farmers keep farming to fund spawns, and spawning is opportunistically used to grow our force when wheat allows.

Python implementation (class SmartAdaptation)

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Split villagers by role
        farmers = [c for c in components if getattr(c, "role", "") == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", "") == "Warrior"]

        n_farmers = len(farmers)
        n_warriors = len(warriors)

        # Wheat available for spawning (read-only in the problem statement)
        available_wheat = getattr(getattr(environment, "farm", None), "wheat", 0)

        # Determine how many spawn pairs we should allocate to maximize spawns
        best_f, best_w = 0, 0
        best_total = -1
        # f: number of spawn-farmer pairs
        for f in range(0, n_farmers // 2 + 1):
            # w: number of spawn-warrior pairs
            max_w_for_f = (n_farmers - 2 * f) // 2
            for w in range(0, max_w_for_f + 1):
                if 10 * f + 12 * w <= available_wheat:
                    total = f + w
                    if total > best_total:
                        best_total = total
                        best_f = f
                        best_w = w

        # Assign groups
        # Spawn groups require two farmers per pair
        to_spawn_f = 2 * best_f
        to_spawn_w = 2 * best_w

        # Assign farmers: first to spawn farmer, next to spawn warrior, rest to farm
        for idx, c in enumerate(farmers):
            if idx < to_spawn_f:
                environment.assign_group(c, "spawn farmer")
            elif idx < to_spawn_f + to_spawn_w:
                environment.assign_group(c, "spawn warrior")
            else:
                environment.assign_group(c, "farm")

        # All Warriors go to the Cave (to be attacked later)
        for c in warriors:
            environment.assign_group(c, "cave")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In Cave, Warriors should Attack; Farmers go back to Village
        for c in components:
            if getattr(c, "role", "") == "Warrior":
                environment.assign_group(c, "attack")
            else:
                # Farmers go to Village
                environment.assign_group(c, "village")
```