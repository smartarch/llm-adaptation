"""
Adaptation strategy: SmartAdaptation

Overview:
- The goal is to kill the Dragon as fast as possible by smartly grouping villagers
  in the village and in the cave. All Warriors should target the Dragon by moving
  to the Cave and attacking. Farmers stay in the Village and either farm or help
  spawn new villagers (both Farmers and Warriors) to accelerate the army growth.

In Village (assign_in_village):
- Warriors are always moved to the cave (attack group) to maximize damage output.
- Farmers are split into three sub-strategies:
  1) spawn farmer: for every two farmers assigned here and 10 wheat, a new Farmer
     is spawned. This yields more farmers who can farm or later be sent to spawn more.
  2) spawn warrior: for every two villagers assigned here and 12 wheat, a new Warrior
     is spawned. This can provide additional combatants to be sent to the cave.
  3) farm: remaining farmers stay in the village to farm wheat at bandwith 5 wheat per
     farmer.

- Allocation is done by an exhaustive search for x (spawn farmer), y (spawn warrior),
  and z (farm) allocations among farmers in the village to maximize total spawns:
  total_spawns = min(x//2, wheat//10) + min(y//2, (wheat - 10*min(x//2,wheat//10))//12)

- The two-spawner constraint ensures we only count viable spawn events, and we also respect
  the available wheat.

- All existing Warriors are moved to the cave; all Farmers are allocated to one of the three
  farmer-related groups (spawn farmer, spawn warrior, or farm) as per the optimization.

In Cave (assign_in_cave):
- All Warriors should stay in the cave and attack the Dragon (attack group).
- All Farmers should move back to the Village (village group) to continue farming or spawning
  villagers, since the strategy emphasizes village-based growth.

Note:
- The environment.assign_group(component, group_id) method is used to assign components to
  groups. The code guards against missing group_ids by checking the presence of group names
  in the provided list (group_ids).

This implementation adheres to the required interface and constraints:
- Class named SmartAdaptation derived from DragonHuntAdaptation
- Implement assign_in_village and assign_in_cave
- Use environment.assign_group(...) for group assignments
"""

from typing import List
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _safe_assign(self, environment, component, group_id, group_ids):
        if group_id in group_ids:
            environment.assign_group(component, group_id)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Divide villagers in the Village into:
        - farm: stay in the Village and farm wheat
        - cave: go to the Cave (this will be handled by assigning Warriors to cave)
        - spawn farmer: for every two villagers assigned to this group and 10 wheat, a new Farmer is spawned
        - spawn warrior: for every two villagers assigned to this group and 12 wheat, a new Warrior is spawned

        Strategy:
        - Move all Warriors to the cave's "cave" group (or "attack" if available in cave step)
        - Partition Farmers into spawn_farm, spawn_warrior, and farm to maximize total spawns
        - Use a small exhaustive search over allocations to maximize spawns given current wheat
        """
        farm_group = "farm"
        cave_group = "cave"
        spawn_farm_group = "spawn farmer"
        spawn_war_group = "spawn warrior"

        # Classify farmers and warriors
        farmers: List = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors: List = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Step 1: Move all warriors to cave (attack)
        for w in warriors:
            self._safe_assign(environment, w, cave_group, group_ids)

        # Step 2: Partition farmers into spawn_farm / spawn_war / farm to maximize spawns
        n_farm = len(farmers)
        available_wheat = getattr(environment, "farm").wheat if hasattr(environment, "farm") else 0

        best_alloc = (0, 0, n_farm)  # (x for spawn_farm, y for spawn_war, z for farm)
        best_spawns = -1

        # Exhaustive search over possible allocations of farmers to the 3 groups
        for x in range(0, n_farm + 1):  # number to spawn farmer
            for y in range(0, n_farm - x + 1):  # number to spawn warrior
                z = n_farm - x - y  # number to farm
                W = available_wheat

                spawns_farm = min(x // 2, W // 10)
                W_after_farm = W - spawns_farm * 10
                spawns_war = min(y // 2, W_after_farm // 12)

                total_spawns = spawns_farm + spawns_war
                if total_spawns > best_spawns:
                    best_spawns = total_spawns
                    best_alloc = (x, y, z)

        x, y, z = best_alloc

        # Assign farmers according to best_alloc
        idx = 0
        # Spawn farmers
        for _ in range(x):
            if idx < n_farm:
                self._safe_assign(environment, farmers[idx], spawn_farm_group, group_ids)
                idx += 1
        # Spawn warriors
        for _ in range(y):
            if idx < n_farm:
                self._safe_assign(environment, farmers[idx], spawn_war_group, group_ids)
                idx += 1
        # Remaining farmers farm
        for _ in range(z):
            if idx < n_farm:
                self._safe_assign(environment, farmers[idx], farm_group, group_ids)
                idx += 1

        # If there are any other villagers not categorized (defensive safety)
        # assign them to farm by default to ensure every villager is in some group
        # (Though in this model, all villagers should be farmers or warriors)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Divide villagers in the Cave into:
        - attack: Attack the Dragon
        - cave: Stay in the Cave
        - village: Go to the Village

        Strategy:
        - All Warriors in Cave go to attack
        - All Farmers in Cave go back to the Village (to continue farming/spawning)
        - The cave group can stay with a potential subset if needed, but to follow the
          strategy, we move farmers back to village.
        """
        attack_group = "attack"
        cave_group = "cave"
        village_group = "village"

        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                self._safe_assign(environment, c, attack_group, group_ids)
            else:
                # Farmers go to Village
                self._safe_assign(environment, c, village_group, group_ids)