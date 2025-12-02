# Strategy implementation: dynamic, tiered early Warrior spawns with capped aggression.
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
        - Tiered early Warrior spawns with a cap per step to balance aggression and wheat:
            - step <= 2: cap up to 2 Warrior spawns
            - step == 3: cap up to 3 Warrior spawns
            - step >= 4: cap up to 1 Warrior spawn
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
        remaining = list(farmers)

        # Tiered early Warrior spawns with a cap
        cap = 2 if step <= 2 else (3 if step == 3 else 1)
        s_w_max = min(len(remaining) // 2, wheat // 12)
        s_w = min(s_w_max, cap)

        idx = 0
        for _ in range(s_w):
            environment.assign_group(remaining[idx], "spawn warrior")
            environment.assign_group(remaining[idx + 1], "spawn warrior")
            idx += 2
            wheat -= 12

        remaining = remaining[idx:]

        # Spawn Farmers greedily
        s_f = min(len(remaining) // 2, wheat // 10)
        for _ in range(s_f):
            environment.assign_group(remaining[2 * _], "spawn farmer")
            environment.assign_group(remaining[2 * _ + 1], "spawn farmer")
            wheat -= 10

        # Remaining farmers go to farming
        rem_start = 2 * s_f
        for c in remaining[rem_start:]:
            environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Cave allocation:
        - All Warriors -> "attack" (attack the Dragon)
        - Farmers -> "village" (return to Village)
        """
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")