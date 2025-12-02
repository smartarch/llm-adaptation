"""
Strategy note and reasoning (further aggressiveness with a small sustainability safeguard):

Goal:
- Reduce the number of turns to kill the Dragon by pushing for faster early DPS via Warrior spawns,
- While not completely starving wheat production, to allow ongoing spawns over time.

Key ideas:
- Warriors deal more damage than Farmers. Early Warrior spawns can accelerate dragon DPS quickly.
- Spawning costs:
  - Warrior-spawn: 2 villagers + 12 wheat
  - Farmer-spawn: 2 villagers + 10 wheat
- Wheat is earned by Farmers farming. To keep spawning possible over multiple turns, we should ensure some Farmers keep farming, but we can temporarily deprioritize farming to accelerate early Warrior spawns.
- Warriors should still be moved to the Cave to attack as soon as possible; Farmers stay in Village to farm or participate in spawns.

Adaptive plan (new behavior):
- In assign_in_village:
  - Move all Warriors to the Cave immediately.
  - Determine reserve_for_farming based on the current step:
    - If step < 4: reserve_for_farming = 0 (aggressively spawn Warriors early)
    - Else, use a conservative heuristic:
      - If nf >= 4: reserve_for_farming = 2
      - Else if nf >= 2: reserve_for_farming = 1
      - Else: 0
  - Compute available_for_spawns = max(0, nf - reserve_for_farming).
  - Use wheat to spawn as many Warriors as possible first (spawn_war_count).
  - With remaining farmers and wheat, spawn Farmers (spawn_farm_count).
  - Assign Farmers:
    - First reserve_for_farming farmers stay in "farm"
    - Next spawn_war_count farmers to "spawn warrior"
    - Next spawn_farm_count farmers to "spawn farmer"
    - Remaining farmers to "farm"
- In assign_in_cave:
  - Warriors -> "attack"; Farmers -> "village"

This strategy keeps a dynamic, step-aware aggression: it aggressively grows Warrior numbers in the very early steps, then gradually rebalances to sustain spawning and farming for continued growth.

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

        # Step-based reserve for farming
        if step < 4:
            reserve_for_farming = 0
        else:
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