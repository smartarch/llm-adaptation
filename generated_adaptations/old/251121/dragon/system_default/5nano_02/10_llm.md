```py
"""
Strategy note and reasoning:

Goal: Improve win rate by aggressively increasing Dragon DPS early while maintaining wheat production.

Key ideas:
- Warriors deal more damage in combat (3 per attack) than Farmers (1).
- Spawning costs:
  - Warrior-spawn: 2 villagers + 12 wheat
  - Farmer-spawn: 2 villagers + 10 wheat
- Wheat comes from Farmers farming; we should keep at least one Farmer farming to sustain wheat, and use the rest to spawn more warriors as quickly as possible (subject to wheat availability).
- Farmers should remain in the Village to farm or spawn, per the rules, while Warriors should be moved to the Cave to attack.

Adaptive plan:
- In assign_in_village:
  - Move all Warriors to the Cave immediately (they will attack in the cave step).
  - For Farmers, reserve one for farming to maintain wheat production.
  - Use remaining Farmers to spawn Warriors first (as many as possible given wheat and available farmers).
  - With any remaining Farmers and remaining wheat, spawn Farmers.
  - Any farmers not used for spawning stay as Farmers (farm).
- In assign_in_cave:
  - Warriors go to "attack"; Farmers return to "village" for farming/spawning.

This approach prioritizes early DPS growth via Warrior spawns while maintaining wheat production for continuous spawning, aiming to shorten the time to kill the Dragon.

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

        total_farmers = len(farmers)
        if total_farmers == 0:
            return

        # Reserve at least one Farmer for farming to keep wheat production going
        reserve_for_farming = 1
        available_for_spawns = max(0, total_farmers - reserve_for_farming)

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
        # - idx 0 -> stay farming in village
        # - next spawn_war_count -> spawn warriors
        # - next spawn_farm_count -> spawn farmers
        # - any remainder -> farm
        for idx, f in enumerate(farmers):
            if idx == 0:
                environment.assign_group(f, "farm")
            elif idx <= spawn_war_count:
                environment.assign_group(f, "spawn warrior")
            elif idx <= spawn_war_count + spawn_farm_count:
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