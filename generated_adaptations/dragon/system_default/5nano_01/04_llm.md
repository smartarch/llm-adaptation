Reasoning and adaptation strategy

What I changed and why:
- The previous strategy always moved all Warriors to the cave and greedily spawned new villagers using as much wheat as possible without considering the evolving wheat production vs. attack DPS balance. This can lead to suboptimal growth or excessive risk of losing all villagers before the Dragon dies.
- The new approach introduces a small, adaptive planning window. It keeps a minimal number of Farmers farming to maintain weed production while spawning new villagers when wheat allows. It also becomes more aggressive with spawning as we get closer to the 30-step limit, increasing the chance to quickly raise DPS if the event horizon is short.
- Key elements:
  - Warriors still always head to the cave to attack (as required).
  - Farmers are split into three dynamic roles in the village:
    - farm: stay in village and farm to generate wheat.
    - spawn farmer: two farmers in this group plus 10 wheat produce a new Farmer.
    - spawn warrior: two farmers in this group plus 12 wheat produce a new Warrior.
  - The allocation logic chooses a reasonable minimum number of farmers to stay farming, then uses the remaining farmers to form spawn groups, constrained by current wheat and the two-for-one spawn rule.
  - The strategy is step-aware: as you approach step 30, you tilt toward spawning more to accelerate DPS, while still maintaining some wheat production early on to avoid starving the spawn pipeline.
- This balanced, adaptive spawning should improve the chance to increase the number of Warriors quickly without starving the wheat engine or overexposing villagers to dragon retaliation.

Now the Python implementation:

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Split villagers in village into:
        # - farm: stay in Village and farm
        # - cave: go to the Cave (for Warriors, but handled already by assign_in_village)
        # - spawn farmer: for every two villagers and 10 wheat, spawn a new Farmer
        # - spawn warrior: for every two villagers and 12 wheat, spawn a new Warrior

        # Collect villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        # Warriors should head to cave
        for w in [c for c in components if getattr(c, "role", None) == "Warrior"]:
            environment.assign_group(w, "cave")

        # Adaptive planning based on step and wheat
        wheat = getattr(getattr(environment, "farm", None), "wheat", 0)

        # Determine how many farmers we can afford to keep farming vs spawn
        # Keep a small, safe amount farming to ensure ongoing wheat production
        if len(farmers) <= 1:
            min_keep_farming = len(farmers)  # nothing to spawn if 0 or 1 farmer
        else:
            if step >= 25:
                # Near the end, try to spawn more aggressively, but keep at least 0 farming if possible
                min_keep_farming = max(0, min(2, len(farmers) - 2))
            else:
                # Early/mid game: keep up to 2 farmers farming if possible
                min_keep_farming = min(2, len(farmers) - 1)

        # Index pointer for assigning farmers
        idx = 0

        # 1) Assign farmers who will farm
        for _ in range(min_keep_farming):
            if idx < len(farmers):
                environment.assign_group(farmers[idx], "farm")
                idx += 1

        # 2) Determine how many spawn farmers we can form with remaining farmers and wheat
        remaining_farmers = len(farmers) - idx
        spawn_farm_cap = 0
        if remaining_farmers >= 2 and wheat >= 10:
            # Each spawn farmer event requires 2 farmers and 10 wheat
            spawn_farm_cap = min(remaining_farmers // 2, wheat // 10)

        # 3) Allocate spawn farmer pairs
        for _ in range(spawn_farm_cap):
            if idx + 1 >= len(farmers):
                break
            environment.assign_group(farmers[idx], "spawn farmer")
            environment.assign_group(farmers[idx + 1], "spawn farmer")
            idx += 2

        # 4) After spawning farmers, compute remaining wheat and farmers
        wheat_after_farm_spawns = max(0, wheat - (spawn_farm_cap * 10))
        remaining_after_farm_spawns = len(farmers) - idx

        # 5) Determine how many spawn warriors we can form with the remaining farmers and wheat
        spawn_war_cap = 0
        if remaining_after_farm_spawns >= 2 and wheat_after_farm_spawns >= 12:
            # Each spawn warrior event requires 2 farmers and 12 wheat
            spawn_war_cap = min(remaining_after_farm_spawns // 2, wheat_after_farm_spawns // 12)

        # 6) Allocate spawn warrior pairs
        for _ in range(spawn_war_cap):
            if idx + 1 >= len(farmers):
                break
            environment.assign_group(farmers[idx], "spawn warrior")
            environment.assign_group(farmers[idx + 1], "spawn warrior")
            idx += 2

        # 7) Remaining farmers go to farming
        while idx < len(farmers):
            environment.assign_group(farmers[idx], "farm")
            idx += 1

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave:
        # - Warriors go to attack
        # - Farmers go to village
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```