```python
# Strategy reasoning and adaptation plan (embedded as comments for clarity):
# Objective: Kill the Dragon as fast as possible within the 30-step limit.
# Observations:
# - Warriors deal 3 damage; Farmers deal 1 damage but produce wheat (5) or (2 if farming for warriors).
# - Spawning rules: to spawn a Farmer you need 2 villagers assigned to "spawn farmer" and 10 wheat;
#   to spawn a Warrior you need 2 villagers assigned to "spawn warrior" and 12 wheat.
# - All Warriors should go to the Cave and attack; Farmers stay in the Village and either farm or spawn new villagers.
# - Wheat is the key resource to enable population growth. Spawns increase long-term DPS, but
#   require wheat and two villagers per spawn.
# Strategy:
# - In the Village:
#   - Move all Warriors to the Cave (attack).
#   - Use Farmers to spawn as many new Farmers as possible (greedily) given wheat: pair up two farmers per spawn
#     consuming 10 wheat per spawn.
#   - With any remaining farmers, spawn Warriors as long as there is enough wheat (12 per spawn).
#   - All farmers not used for spawning are assigned to farming to accumulate more wheat for future rounds.
# - In the Cave:
#   - All Warriors stay in the Cave and attack (group "attack").
#   - Farmers in the Cave (if any) should return to the Village (group "village"), since the policy
#     is to keep Farmers in Village for farming or spawning new villagers.
# Rationale:
# - This greedy spawning approach rapidly expands the population when wheat is available, increasing DPS
#   over time, while ensuring immediate DPS from Warriors is applied every turn.
# - By keeping Farmers farming, we maximize wheat production to enable subsequent spawns, accelerating
#   long-term DPS growth and increasing the chance to kill the Dragon earlier than a purely farming strategy.

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
        Divide villagers in the Village into:
        - "farm": Farmers stay to farm
        - "cave": Warriors go to the Cave (attack)
        - "spawn farmer": For every two villagers in this group and 10 wheat, a new Farmer is spawned.
        - "spawn warrior": For every two villagers in this group and 12 wheat, a new Warrior is spawned.
        """
        # Identify current villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # 1) Send all warriors to the Cave to attack
        for w in warriors:
            environment.assign_group(w, "cave")

        # 2) Spawn and farming logic for farmers
        wheat = int(getattr(environment.farm, "wheat", 0))

        # We will pair up farmers to spawn Farmers first, as long as we have wheat
        s_f = min(len(farmers) // 2, wheat // 10)  # number of Farmer spawns we can perform
        idx = 0  # pointer into farmers list for spawning farmers
        for _ in range(s_f):
            environment.assign_group(farmers[idx], "spawn farmer")
            environment.assign_group(farmers[idx + 1], "spawn farmer")
            idx += 2
            wheat -= 10

        # Remaining farmers after spawning Farmers
        remaining = farmers[idx:]

        # Next, spawn Warriors from remaining farmers if possible
        s_w = min(len(remaining) // 2, wheat // 12)  # number of Warrior spawns we can perform
        idx2 = 0
        for _ in range(s_w):
            environment.assign_group(remaining[idx2], "spawn warrior")
            environment.assign_group(remaining[idx2 + 1], "spawn warrior")
            idx2 += 2
            wheat -= 12

        # The rest of the farmers (not used for spawning) go to farming
        for c in remaining[idx2:]:
            environment.assign_group(c, "farm")

        # If there were any other farmers not touched (shouldn't be), ensure they're farmed
        # (The logic above covers all farmers: spawned ones are set to spawn groups; others to farm.)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Divide villagers in the Cave into:
        - "attack": Attack the Dragon
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