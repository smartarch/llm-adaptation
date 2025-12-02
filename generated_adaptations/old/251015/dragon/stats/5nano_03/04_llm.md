```py
"""
Improved adaptation strategy rationale:

- Objective: Increase the chance of killing the Dragon quickly while avoiding catastrophic losses of villagers to the Dragon in the Cave.
- Key observations:
  - Warriors deal significantly more damage per attack (3) than Farmers (1).
  - Spawning rules require two villagers in a spawn group plus a wheat cost (12 for warriors, 10 for farmers).
  - The Dragon can punish villagers in the Cave via AoE (40% chance) or by eating a random villager (20%).
  - All Warriors should eventually end up in the Cave to maximize damage output; Farmers should stay in the Village to farm and/or spawn new villagers.
- Strategy evolution:
  - First, move all Warriors to the Cave so they can contribute to the Dragon-hunt.
  - Spawn Warriors aggressively only if wheat is available and there are enough Farmers to sustain the spawns. This ensures more attackers without starving the Wheat production.
  - After allocating for Warrior spawns, use remaining Farmers and Wheat to spawn Farmers (to sustain long-term wheat production) before resorting to farming for Wheat.
  - Any remaining Farmers are assigned to farming to continue producing Wheat for future turns.
- Rationale:
  - This approach yields a bounded, greedy expansion: it prioritizes increasing attack power early while maintaining a Wheat-producing backbone (Farmers) to support future spawns.
  - It avoids a situation where we spawn too many Farmers (which yields many non-attacking villagers) or too few Warriors (which delays dragon kill).
- Caveats:
  - The simulation’s stochastic dragon retaliation remains a risk; keeping some Farmers in reserve to sustain Wheat production helps long-term viability.
"""

from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        In the Village:
        - Move all Warriors to the Cave (to join the hunt in the cave in subsequent steps).
        - Spawn strategy:
            1) Spawn Warriors as a priority if we have wheat and at least 2 Farmers available.
            2) With remaining Farmers and remaining Wheat, spawn Farmers.
            3) Any remaining Farmers stay to Farm (produce Wheat this turn).
        - All spawned groups are explicit to ensure correct spawning logic by the simulator.
        """
        villagers = list(components)

        # Separate by role
        farmers = [c for c in villagers if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in villagers if getattr(c, "role", None) == "Warrior"]

        # 1) Move all Warriors to the cave (to join the attack in the cave)
        for w in warriors:
            environment.assign_group(w, "cave")

        # 2) Spawning logic for Warriors and Farmers (greedy but bounded)
        wheat = getattr(environment.farm, "wheat", 0)
        n_farmers = len(farmers)

        # Spawn Warriors first (need 2 villagers and 12 wheat per spawn)
        spawns_warriors = 0
        if n_farmers >= 2 and wheat >= 12:
            spawns_warriors = min(n_farmers // 2, wheat // 12)

        spawn_war_members = farmers[: 2 * spawns_warriors]
        remaining_after_war_spawns = farmers[2 * spawns_warriors :]

        # Wheat left after Warrior spawns
        wheat_after_war = wheat - spawns_warriors * 12

        # Spawn Farmers next (need 2 villagers and 10 wheat per spawn)
        spawns_farmers = 0
        if len(remaining_after_war_spawns) >= 2 and wheat_after_war >= 10:
            spawns_farmers = min(len(remaining_after_war_spawns) // 2, wheat_after_war // 10)

        spawn_farm_members = remaining_after_war_spawns[: 2 * spawns_farmers]
        farm_members = remaining_after_war_spawns[2 * spawns_farmers :]

        # 3) Assign groups
        for w in spawn_war_members:
            environment.assign_group(w, "spawn warrior")
        for f in spawn_farm_members:
            environment.assign_group(f, "spawn farmer")
        for f in farm_members:
            environment.assign_group(f, "farm")

        # Note: Any remaining Farmers beyond the above allocations are already assigned to "farm".
        # If there are any Warriors left (shouldn't be, since we moved all to cave), ensure they
        # are in the cave group by re-affirming:
        # for w in warriors:
        #     environment.assign_group(w, "cave")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        In the Cave:
        - All Warriors should attack the Dragon.
        - All Farmers should return to the Village to farm or spawn.
        - The "cave" group is not used for Farmers per the strategy, but remains available if needed.
        """
        for comp in components:
            role = getattr(comp, "role", None)
            if role == "Warrior":
                environment.assign_group(comp, "attack")
            else:
                # Farmers go back to Village
                environment.assign_group(comp, "village")
```