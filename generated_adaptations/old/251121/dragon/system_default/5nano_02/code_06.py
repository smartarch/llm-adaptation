"""
Reasoning and strategy:

Goal: Improve turn efficiency by aggressively growing the villager population with a focus on early DPS from Warriors.

Key observations:
- Warriors contribute more damage when in the Cave (3 per attack) than Farmers (1).
- Spawn mechanics allow expanding the population with wheat, but require two villagers in a spawn group and a wheat cost (10 for Farmer-spawn, 12 for Warrior-spawn).
- Wheat production comes from Farmers farming (5 wheat per Farmer) and is needed to fund spawns. To sustain spawning, we should keep at least one Farmer farming each step to generate wheat.
- Early DPS is valuable to finish the Dragon faster; thus, spawning Warriors early (when possible) is beneficial because they immediately contribute to damage as soon as they reach the Cave.

Improved adaptation strategy:
- In assign_in_village:
  - Move all Warriors to the cave (they will attack in the cave step).
  - For Farmers:
    - Reserve one Farmer to farm to maintain wheat production (if at least one Farmer exists).
    - With the remaining Farmers, spawn Warriors first (to boost early DPS). The number of Warrior spawns is limited by two constraints: villagers available for spawning (each Warrior-spawn consumes 2 Farmers) and wheat available (12 wheat per Warrior-spawn).
    - After allocating Warrior-spawns, spawn Farmers with the leftover Farmers and wheat (10 wheat per Farmer-spawn).
    - Any Farmers not used for spawning will remain in the village to farm (or continue farming).
  - This greedy approach prioritizes early DPS via Warrior spawns while still growing wheat production through the farming farmer and possible Farmer-spawns.
- In assign_in_cave:
  - Move Warriors to "attack" and Farmers to "village" so they can return to farming or spawn in the next step.

This strategy aims to:
- Increase immediate dragon damage with quickly spawned Warriors.
- Maintain wheat production to enable ongoing population growth.
- Balance between aggression (more warriors) and sustainability (continuous wheat production).

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
            # No farmers to allocate; nothing else to do in village
            return

        # Reserve one farmer for farming to keep wheat production going
        reserve_for_farming = 1

        # If there is only one farmer, we can't spawn; rely on farming
        available_for_spawns = max(0, total_farmers - reserve_for_farming)

        wheat = getattr(environment.farm, "wheat", 0)

        # Spawn Warriors first: each spawn requires 2 farmers and 12 wheat
        max_war_spawns = min(available_for_spawns // 2, wheat // 12)
        spawn_war_count = max_war_spawns * 2
        used_wheat_after_war = max_war_spawns * 12

        remaining_farmers_after_war = available_for_spawns - spawn_war_count

        # Then spawn Farmers with remaining wheat: each spawn requires 2 farmers and 10 wheat
        max_farm_spawns = min(remaining_farmers_after_war // 2, (wheat - used_wheat_after_war) // 10)
        spawn_farm_count = max_farm_spawns * 2
        used_wheat_after_farm = used_wheat_after_war + max_farm_spawns * 10

        # Enumerate and assign groups for farmers
        # We map indices to actions:
        # - idx 0 (first farmer) -> stay farming in village
        # - next spawn_war_count farmers -> spawn warriors
        # - next spawn_farm_count farmers -> spawn farmers
        # - any remaining farmers -> farm
        for idx, f in enumerate(farmers):
            if idx == 0:
                environment.assign_group(f, "farm")
            elif idx <= spawn_war_count:
                environment.assign_group(f, "spawn warrior")
            elif idx <= spawn_war_count + spawn_farm_count:
                environment.assign_group(f, "spawn farmer")
            else:
                environment.assign_group(f, "farm")

        # Note: Wheat accounting is handled by the engine; we simply select the spawn groups
        return

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # Warriors attack; Farmers return to Village
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")