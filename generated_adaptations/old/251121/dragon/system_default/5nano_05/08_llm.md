```py
"""
Reasoning and adaptation strategy (integrated as comments for traceability):
- Objective: improve the chance to win in fewer turns by a more aggressive but controlled spawning policy that prioritizes early Warrior DPS while still maintaining wheat production for ongoing spawns.
- Core ideas:
  1) In the Village, always move existing Warriors to the Cave, so they contribute DPS as soon as possible.
  2) Use Farmers in the Village to spawn new villagers, but balance spawning Warrior villagers (to boost future DPS) with spawning Farmer villagers (to boost wheat production for future spawns).
  3) Spawn Warrior events require 2 Farmers and 12 Wheat; Spawn Farmer events require 2 Farmers and 10 Wheat. We select the number of spawns each step based on current counts and Wheat.
  4) In the Cave, keep Warriors attacking the Dragon; Farmers return to the Village to farm/spawn in subsequent steps.
- Effect: faster ramp-up of DPS in cave while maintaining a steady Wheat supply to enable continued population growth and thus potentially kill the Dragon earlier within the 30-step limit.

Code implementation:
"""

from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Strategy in Village:
        - Move all existing Warriors to the Cave (cave group) to start dealing damage early.
        - Use Farmers to spawn new villagers:
            * First, spawn as many Warriors as possible given Wheat (requires 2 Farmers per Warrior spawn and 12 Wheat).
            * Then, with remaining Farmers, spawn as Farmers (requires 2 Farmers per Farmer spawn and 10 Wheat).
            * Any remaining Farmers stay in Village to farm.
        - This approach ramps up Warrior numbers while ensuring Wheat production continues.
        """
        # Separate villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Always move existing Warriors to the Cave
        for c in warriors:
            environment.assign_group(c, "cave")

        # Current Wheat in Farm (default 0 if farm not present)
        W = 0
        farm = getattr(environment, "farm", None)
        if farm is not None:
            W = getattr(farm, "wheat", 0)

        # Spawn Warriors first (maximize early DPS)
        p_war = min(len(farmers) // 2, W // 12)

        # Villagers selected for Warrior spawns
        spawn_war_group = farmers[:2 * p_war]
        for c in spawn_war_group:
            environment.assign_group(c, "spawn warrior")

        # Wheat remaining after Warrior spawns
        W_after_war = W - p_war * 12

        # Remaining Farmers available for Warrior spawns (2 farmers each)
        remaining_farmers_after_war_spawns = len(farmers) - 2 * p_war

        # Spawn Farmers next with remaining Wheat
        p_farm = min(remaining_farmers_after_war_spawns // 2, W_after_war // 10)
        spawn_farm_group = farmers[2 * p_war: 2 * p_war + 2 * p_farm]
        for c in spawn_farm_group:
            environment.assign_group(c, "spawn farmer")

        # Remaining Farmers go to farming
        farmers_to_farm = farmers[2 * p_war + 2 * p_farm :]
        for c in farmers_to_farm:
            environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Strategy in Cave:
        - Warriors attack the Dragon
        - Farmers go back to the Village to farm/spawn in future steps
        """
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```