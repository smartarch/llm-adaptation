```python
# Strategy reasoning (embedded as comments for clarity):
# Objective: Increase the speed of killing the Dragon within the 30-step limit.
# Key observations:
# - Warriors deal 3 damage when attacking; Farmers deal 1 damage but provide wheat by farming (5 wheat per farming turn for a Farmer, 2 wheat per farming turn when a Warrior farms—depending on role, but the exact per-turn wheat mechanics are abstracted by the environment).
# - Spawning rules require 2 villagers in a spawn group and a wheat cost (10 for a Farmer, 12 for a Warrior) to produce a new villager of the corresponding type.
# - All Warriors should go to the Cave and attack; Farmers stay in the Village to farm or spawn.
# - Dragon retaliation is dangerous: it can hit all villagers in the Cave with 1 damage (40% chance) or eat one random villager in the Cave (20%).
# - To win faster, we want to accelerate early DPS (more Warriors earlier) while not starving wheat production, which powers future spawns of more villagers.

# Improved strategy:
# - In the Village:
#   - Move all Warriors to the Cave (attack) to maximize immediate DPS.
#   - Use Farmers to spawn new Farmers first (to boost long-term wheat production).
#   - Introduce an early-aggro phase: in the first few steps, opportunistically spawn Warriors as well if we have enough wheat and at least 4 Farmers remaining, to increase early DPS.
#   - After the early-aggro window, revert to spawning Farmers first, then Warriors with any remaining wheat.
#   - Any Farmers not used for spawning are assigned to farming to accumulate more wheat for future rounds.
# - In the Cave:
#   - Keep all Warriors in the "attack" group to maximize damage to the Dragon.
#   - Any Farmers in the Cave should head back to the Village (group "village"), since they are not meant to stay in the Cave under this strategy.

# This approach aims to balance immediate DPS from early Warrior spawns with longer-term wheat production from Farmers, while keeping a compact and steady force in the cave to minimize risk from dragon retaliation.

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
        In the Village:
        - Move all Warriors to the Cave (attack).
        - Use Farmers to spawn new Farmers first (consumes 10 wheat per spawn).
        - If early-aggro window is active (step <= 4) and there are at least 4 Farmers and wheat >= 12,
          spawn Warriors as well (consumes 12 wheat per spawn for each pair).
        - Remaining Farmers go to farming to accumulate wheat.
        - This balances immediate DPS growth with wheat production for future spawns.
        """
        # Separate farmers and warriors in the village
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # 1) Send all warriors to the Cave to attack
        for w in warriors:
            environment.assign_group(w, "cave")

        # 2) Spawning and farming logic for farmers
        wheat = int(getattr(environment.farm, "wheat", 0))

        # Early-aggro phase: step 0..4
        remaining_farmers = list(farmers)
        if step <= 4:
            # Aggressively spawn Warriors if possible (needs 2 farmers + 12 wheat)
            s_w = min(len(remaining_farmers) // 2, wheat // 12)
            if s_w > 0:
                for _ in range(s_w):
                    environment.assign_group(remaining_farmers[0], "spawn warrior")
                    environment.assign_group(remaining_farmers[1], "spawn warrior")
                    remaining_farmers = remaining_farmers[2:]
                    wheat -= 12

            # Then spawn Farmers with any remaining farmers
            s_f = min(len(remaining_farmers) // 2, wheat // 10)
            for _ in range(s_f):
                environment.assign_group(remaining_farmers[0], "spawn farmer")
                environment.assign_group(remaining_farmers[1], "spawn farmer")
                remaining_farmers = remaining_farmers[2:]
                wheat -= 10

            # The rest go to farming
            for c in remaining_farmers:
                environment.assign_group(c, "farm")

        else:
            # Normal phase: spawn farmers first, then spawn warriors with remaining
            s_f = min(len(remaining_farmers) // 2, wheat // 10)
            idx = 0
            for _ in range(s_f):
                environment.assign_group(remaining_farmers[idx], "spawn farmer")
                environment.assign_group(remaining_farmers[idx + 1], "spawn farmer")
                idx += 2
                wheat -= 10

            remaining = remaining_farmers[idx:]

            # Spawn warriors from remaining if possible
            s_w = min(len(remaining) // 2, wheat // 12)
            idx2 = 0
            for _ in range(s_w):
                environment.assign_group(remaining[idx2], "spawn warrior")
                environment.assign_group(remaining[idx2 + 1], "spawn warrior")
                idx2 += 2
                wheat -= 12

            # Remaining farmers go to farming
            for c in remaining[idx2:]:
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        In the Cave:
        - All Warriors -> "attack" (attack the Dragon)
        - Farmers -> "village" (return to Village)
        """
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```