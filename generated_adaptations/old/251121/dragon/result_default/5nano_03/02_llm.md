```python
# Strategy reasoning (embedded as comments for clarity):
# Objective:
# - Kill the Dragon as fast as possible.
# - Warriors are more efficient at dealing damage; Farmers help generate wheat and can spawn new villagers.
# - All Warriors should go to the Cave and attack the Dragon.
# - All Farmers should stay in the Village and either farm or spawn new villagers.
#
# Practical adaptation plan:
# 1) In the Village:
#    - Move all Warriors to the Cave (assign to "cave") so they can be deployed to attack.
#    - Manage Farmers:
#        - Use some Farmers to spawn new Farmers via the "spawn farmer" group.
#        - Use some Farmers to spawn new Warriors via the "spawn warrior" group (optional, if wheat allows).
#        - Remaining Farmers stay in the Village and go to the "farm" group to produce wheat.
#    - Spawning rules:
#        - To spawn a Farmer: need 2 villagers in "spawn farmer" and at least 10 wheat.
#        - To spawn a Warrior: need 2 villagers in "spawn warrior" and at least 12 wheat.
#        - We implement a simple greedy spawning:
#            - First pair up Farmers to spawn Farmers as long as there is wheat (10) and at least 2 Farmers available.
#            - Then, if there are still two Farmers left and wheat >= 12, spawn Warriors (pair them).
#            - Any Farmers not used for spawning go to "farm".
# 2) In the Cave:
#    - Move all Warriors present in the Cave to the "attack" group to surface-damage the Dragon.
#    - Move any Farmers in the Cave to the "village" group to return to the Village (Farmers should not stay in Cave per strategy).
# 3) Other notes:
#    - We rely on given environment attributes:
#        environment.farm.wheat — current wheat amount.
#        environment.dragon.hp   — Dragon HP (read-only for us here).
#    - The actual combat dynamics (Dragon retaliation, HP changes, spawning outcomes) are handled by the game engine.
#    - Our heuristic aims to balance wheat production with incremental population growth to increase DPS over time.

from typing import List
import abc

# Import the base abstract class from the provided module
try:
    from generated_adaptations.base_classes.dragon import DragonHuntAdaptation
except Exception:
    # Fallback for environments where import paths differ during testing
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
        Assign villagers in the Village into:
        - "farm": Farmers stay in Village to farm
        - "cave": Warriors go to Cave (attack)
        - "spawn farmer": For future Farmer spawns (needs two villagers and 10 wheat)
        - "spawn warrior": For future Warrior spawns (needs two villagers and 12 wheat)
        """
        # Separate farmers and warriors in the village
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # 1) Send all warriors to the Cave to attack
        for w in warriors:
            environment.assign_group(w, "cave")

        # 2) Manage farmers for farming and spawning
        # We will track wheat available for spawning
        wheat = int(getattr(environment.farm, "wheat", 0))

        # Copy list of farmers to mutate while assigning
        remaining_farmers = list(farmers)

        # Spawn farmers greedily: take two farmers at a time, require >=10 wheat
        i = 0
        while len(remaining_farmers) - i >= 2 and wheat >= 10:
            c1 = remaining_farmers[i]
            c2 = remaining_farmers[i + 1]
            environment.assign_group(c1, "spawn farmer")
            environment.assign_group(c2, "spawn farmer")
            wheat -= 10
            i += 2  # consumed two farmers for one spawn

        # After attempting farmer spawns, the rest go to farming or stay for future spawns
        for j in range(i, len(remaining_farmers)):
            environment.assign_group(remaining_farmers[j], "farm")

        # Optional: Spawn warriors if enough wheat and enough farmers left (after farmer spawns)
        # Use any remaining farmers to spawn warriors, if possible.
        remaining_farmers_after = remaining_farmers[i:]
        k = 0
        while len(remaining_farmers_after) - k >= 2 and wheat >= 12:
            c1 = remaining_farmers_after[k]
            c2 = remaining_farmers_after[k + 1]
            environment.assign_group(c1, "spawn warrior")
            environment.assign_group(c2, "spawn warrior")
            wheat -= 12
            k += 2

        # Remaining farmers (if any) that couldn't spawn are sent to farm
        for t in range(k, len(remaining_farmers_after)):
            environment.assign_group(remaining_farmers_after[t], "farm")

        # If there were any farmers not processed in the earlier loops due to list append logic,
        # ensure they are assigned to a sane final state (farm). The above covers all.

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Assign villagers in the Cave into:
        - "attack": Warriors go here to attack the Dragon
        - "cave": Stay in the Cave
        - "village": Go to the Village
        Strategy: move all Warriors to "attack"; move Farmers back to "village".
        """
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                # Farmers should head back to the Village
                environment.assign_group(c, "village")
```