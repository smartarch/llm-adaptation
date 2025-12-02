# Strategy reasoning (embedded as comments for clarity):
# Objective:
# - Kill the Dragon as fast as possible within the 30-step limit.
# Observations:
# - Warriors deal 3 damage when attacking; Farmers deal 1 damage but produce wheat over time.
# - Spawning rules: to spawn a Farmer you need 2 villagers assigned to "spawn farmer" and 10 wheat; 
#   to spawn a Warrior you need 2 villagers assigned to "spawn warrior" and 12 wheat.
# - All Warriors should go to the Cave and attack; Farmers stay in the Village to farm or spawn.
# - Wheat is the critical resource to enable population growth, which increases future DPS.
#
# Improved strategy (dynamic and more proactive early DPS):
# - In the Village:
#   - Move all Warriors to the Cave (attack) for immediate DPS.
#   - In early turns (step <= 2), try to spawn up to 1 Warrior using 2 farmers if wheat >= 12.
#   - In early turns (step <= 4), if there are at least 4 farmers and wheat >= 24, spawn up to 2 additional Warriors
#     (using 4 farmers and 24 wheat) to boost early DPS.
#   - After the early aggression window, spawn Farmers as many times as possible (two farmers per spawn, cost 10 wheat).
#   - Remaining farmers go to farming to accumulate more wheat for future spawns.
# - In the Cave:
#   - Keep all Warriors in the "attack" group to maximize Dragon damage.
#   - Move Farmers back to the Village (they belong there for farming/spawning).
#
# Rationale:
# - This strategy provides a controlled early DPS boost via up to 3 Warrior spawns in the very early turns,
#   balanced by aggressive wheat farming to enable further spawns. The goal is to reach higher DPS faster
#   while maintaining a sustainable wheat pipeline for subsequent turns.

from typing import List
import abc

# Import the base abstract class from the provided module
try:
    from generated_adaptations.base_classes.dragon import DragonHuntAdaptation
except Exception:
    class DragonHuntAdaptation(abc.ABC):
        def __init__(self, **kwargs):
            super().__init__()

        @abc.abstractmethod
        def assign_in_village(self, components, environment, group_ids, step: int):
            pass

        @abc.abstractmethod
        def assign_in_cave(self, components, environment, group_ids, step: int):
            pass


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Village allocation:
        - Move all Warriors to cave (attack) for immediate DPS.
        - Early aggressive Warrior spawns:
            - If step <= 2 and at least 2 farmers and wheat >= 12, spawn 1 Warrior (uses 2 farmers, 12 wheat).
            - If step <= 4 and at least 4 farmers remaining and wheat >= 24, spawn 2 more Warriors (uses 4 farmers, 24 wheat).
        - After early spawns, spawn Farmers greedily (two farmers per spawn, cost 10 wheat).
        - Remaining farmers go to farming (to accumulate wheat for future spawns).
        """
        # Separate farmers and warriors currently in the village
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # 1) Send all warriors to the Cave to attack
        for w in warriors:
            environment.assign_group(w, "cave")

        # 2) Spawning and farming logic for farmers
        wheat = int(getattr(environment.farm, "wheat", 0))

        # Work with a local copy of farmers to decide spawns
        remaining_farmers = list(farmers)

        # Early aggressive Warrior spawns
        # a) First potential Warrior spawn (step <= 2)
        if step <= 2 and len(remaining_farmers) >= 2 and wheat >= 12:
            environment.assign_group(remaining_farmers[0], "spawn warrior")
            environment.assign_group(remaining_farmers[1], "spawn warrior")
            remaining_farmers = remaining_farmers[2:]
            wheat -= 12

        # b) Second potential Warrior spawns (step <= 4)
        if step <= 4 and len(remaining_farmers) >= 4 and wheat >= 24:
            environment.assign_group(remaining_farmers[0], "spawn warrior")
            environment.assign_group(remaining_farmers[1], "spawn warrior")
            environment.assign_group(remaining_farmers[2], "spawn warrior")
            environment.assign_group(remaining_farmers[3], "spawn warrior")
            remaining_farmers = remaining_farmers[4:]
            wheat -= 24

        # Spawn Farmers with any remaining farmers
        spawns_f = min(len(remaining_farmers) // 2, wheat // 10)
        idx = 0
        for _ in range(spawns_f):
            environment.assign_group(remaining_farmers[idx], "spawn farmer")
            environment.assign_group(remaining_farmers[idx + 1], "spawn farmer")
            idx += 2
            wheat -= 10

        # Remaining farmers go to farming
        for c in remaining_farmers[idx:]:
            environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Cave allocation:
        - All Warriors -> "attack" (attack the Dragon)
        - Farmers -> "village" (return to Village)
        """
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")