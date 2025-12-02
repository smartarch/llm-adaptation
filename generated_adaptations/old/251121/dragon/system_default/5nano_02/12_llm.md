```py
"""
Strategy note and reasoning (improved aggressiveness with sustainability):

Goal: Reduce the number of turns to kill the Dragon by:
- Increasing early Dragon DPS via rapid Warrior spawning, but
- Maintaining wheat production by keeping several Farmers farming each step, so spawning can continue over time.
- Warriors should still be deployed to the Cave to attack as soon as possible.

Key improvement:
- Instead of always reserving only 1 Farmer for farming, reserve more when there are enough Farmers (e.g., 2 when nf >= 4). This boosts wheat production (2 * 5 = 10 wheat per step) and enables more future spawns, potentially increasing DPS faster over time without starving spawning.

Adaptive plan:
- In assign_in_village:
  - Move all Warriors to the Cave (to prepare for attack in the cave step).
  - Let nf be the number of Farmers.
  - Determine reserve_for_farming:
    - If nf >= 4: reserve_for_farming = 2
    - Else if nf >= 2: reserve_for_farming = 1
    - Else: reserve_for_farming = 0
  - Compute available_for_spawns = max(0, nf - reserve_for_farming).
  - Use wheat to spawn as many Warriors as possible first: max_war_spawns = min(available_for_spawns // 2, wheat // 12).
  - After Warrior spawns, compute remaining farmers and wheat, then spawn Farmers: max_farm_spawns = min(remaining_for_warriors // 2, remaining_wheat // 10).
  - Assign Farmers:
    - First reserve_for_farming Farmers stay in "farm".
    - Next max_war_spawns * 2 Farmers go to "spawn warrior".
    - Next max_farm_spawns * 2 Farmers go to "spawn farmer".
    - Any remaining Farmers go to "farm".
- In assign_in_cave:
  - Warriors -> "attack"; Farmers -> "village".

This approach aims to create more Warriors quickly while sustaining wheat production through a larger farming base, with the goal of killing the Dragon faster.

"""

from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # All Warriors should go to the Cave (while in village)
        for w in warriors:
            environment.assign_group(w, "cave")

        nf = len(farmers)
        if nf == 0:
            return

        # Determine reserve_for_farming based on population
        if nf >= 4:
            reserve_for_farming = 2
        elif nf >= 2:
            reserve_for_farming = 1
        else:
            reserve_for_farming = 0

        available_for_spawns = max(0, nf - reserve_for_farming)

        wheat = getattr(environment.farm, "wheat", 0)

        # Spawn Warriors first: each spawn requires 2 farmers and 12 wheat
        max_war_spawns = min(available_for_spawns // 2, wheat // 12)
        spawn_war_count = max_war_spawns * 2
        wheat_after_war = wheat - (max_war_spawns * 12)

        remaining_farmers_after_war = available_for_spawns - spawn_war_count

        # Then spawn Farmers with remaining wheat: each spawn requires 2 farmers and 10 wheat
        max_farm_spawns = min(remaining_farmers_after_war // 2,
                              wheat_after_war // 10)
        spawn_farm_count = max_farm_spawns * 2

        # Assign groups for farmers
        # - idx < reserve_for_farming -> stay farming
        # - next spawn_war_count -> spawn warriors
        # - next spawn_farm_count -> spawn farmers
        # - remaining -> farm
        for idx, f in enumerate(farmers):
            if idx < reserve_for_farming:
                environment.assign_group(f, "farm")
            elif idx < reserve_for_farming + spawn_war_count:
                environment.assign_group(f, "spawn warrior")
            elif idx < reserve_for_farming + spawn_war_count + spawn_farm_count:
                environment.assign_group(f, "spawn farmer")
            else:
                environment.assign_group(f, "farm")

        return

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # Warriors attack; Farmers stay in Village
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```