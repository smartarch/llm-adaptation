```python
# Strategy rationale (embedded as comments for clarity):
# Objective:
# - Kill the Dragon as fast as possible within the 30-step limit.
# Observations:
# - Warriors deal 3 damage when attacking; Farmers deal 1 damage but produce wheat over time.
# - Spawning rules: to spawn a Farmer you need 2 villagers assigned to "spawn farmer" and 10 wheat; 
#   to spawn a Warrior you need 2 villagers assigned to "spawn warrior" and 12 wheat.
# - All Warriors should go to the Cave and attack; Farmers stay in the Village to farm or spawn.
# - Dragon retaliation can hit all villagers in the Cave (40% chance for -1 HP each) or eat one random villager in the Cave (20%).
# - Wheat is the critical resource to enable population growth, which increases future DPS.
#
# Improved strategy:
# - In the Village:
#   - Move all Warriors to the Cave to maximize immediate DPS.
#   - Use Farmers to spawn new Warriors early (to boost DPS quickly) when there is enough wheat and at least 4 Farmers available.
#     This accelerates early damage output.
#   - After attempting early Warrior spawns, spawn Farmers with any remaining wheat (to sustain wheat production for future spawns).
#   - Any Farmers not used for spawning are assigned to farming.
# - In the Cave:
#   - Keep all Warriors in the "attack" group to maximize damage to the Dragon.
#   - Move Farmers in the Cave back to the Village (they belong inVillage for farming/spawning).
# - This approach balances immediate DPS with wheat-driven growth, aiming to reduce total turns to kill.
#
# Implementation notes:
# - We always assign Warriors in Village to the "cave" group so they can start attacking immediately.
# - We spawn at most a small, controlled number of Warriors early (to avoid depleting wheat too fast) 
#   but enough to improve early DPS in most scenarios.
# - Spawns consume wheat; we track wheat in local variables but rely on the environment to update states after the turn.

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
        - Move all Warriors to cave (attack).
        - Attempt a small early phase to spawn Warriors if there are at least 4 Farmers and enough wheat.
        - Then spawn Farmers if wheat allows.
        - Finally, send any remaining Farmers to farming.
        """
        # Separate farmers and warriors currently in the village
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # 1) Send all warriors to the Cave to attack
        for w in warriors:
            environment.assign_group(w, "cave")

        # 2) Spawning logic for farmers and optional early warrior spawns
        wheat = int(getattr(environment.farm, "wheat", 0))

        # Work with a local copy of farmers to decide spawns
        remaining_farmers = list(farmers)

        # Early-aggro: try to spawn up to 2 new Warriors if we have enough farmers and wheat
        # Conditions: need 4 farmers and at least 24 wheat to spawn 2 new Warriors (two pairs)
        if step <= 4 and len(remaining_farmers) >= 4 and wheat >= 24:
            spawns_warrior = 2  # attempt to spawn 2 new warriors
            idx = 0
            for _ in range(spawns_warrior):
                environment.assign_group(remaining_farmers[idx], "spawn warrior")
                environment.assign_group(remaining_farmers[idx + 1], "spawn warrior")
                idx += 2
                wheat -= 12
            remaining_farmers = remaining_farmers[idx:]

        # After any early-warrior spawns, spawn Farmers if possible
        s_f = min(len(remaining_farmers) // 2, wheat // 10)
        idx_f = 0
        for _ in range(s_f):
            environment.assign_group(remaining_farmers[idx_f], "spawn farmer")
            environment.assign_group(remaining_farmers[idx_f + 1], "spawn farmer")
            idx_f += 2
            wheat -= 10

        # Remaining farmers go to farming (to accumulate more wheat)
        for c in remaining_farmers[idx_f:]:
            environment.assign_group(c, "farm")

        # Note: New villagers spawned via "spawn farmer" or "spawn warrior" will appear in subsequent turns.

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
```