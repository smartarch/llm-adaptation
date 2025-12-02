```py
"""
Aggressive lookahead adaptation v7

Idea:
- Always send all Warriors to the Cave to attack.
- In the Village, spawn farmers as aggressively as possible given current Farmers (F) and Wheat.
  Then, using whatever Wheat remains, spawn Warriors as soon as possible.
- This eliminates per-step spawn caps and aims to ramp up Wheat and DPS faster, reducing overall steps to kill the Dragon.
- All remaining Farmers go back to farming in the Village.

Notes:
- Spawns continue to require 2 villagers in the spawn group and the respective Wheat cost (10 for farmers, 12 for warriors).
- This strategy remains deterministic per step and respects the constraint that all Warriors go to the Cave.

"""

from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Split villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        F = len(farmers)
        # W = len(warriors)  # not used directly, but kept for readability

        # Wheat available at the Farm
        wheat = 0
        if hasattr(environment, "farm") and hasattr(environment.farm, "wheat"):
            wheat = environment.farm.wheat

        # 1) Move all Warriors to the Cave (attack)
        for w in warriors:
            environment.assign_group(w, "cave")

        # 2) Aggressively spawn farmers: 2 farmers per event, costs 10 wheat
        max_farm_spawn_events = min(F // 2, wheat // 10)
        to_spawn_farmers = max_farm_spawn_events * 2

        idx = 0
        for _ in range(to_spawn_farmers):
            if idx < F:
                environment.assign_group(farmers[idx], "spawn farmer")
                idx += 1

        # 3) Aggressively spawn warriors with remaining farmers and wheat
        remaining_farmers = F - (to_spawn_farmers // 2)
        wheat_after_farm = max(0, wheat - max_farm_spawn_events * 10)

        max_war_spawn_events = min(remaining_farmers // 2, wheat_after_farm // 12)
        to_spawn_warriors = max_war_spawn_events * 2

        for _ in range(to_spawn_warriors):
            if idx < F:
                environment.assign_group(farmers[idx], "spawn warrior")
                idx += 1

        # 4) Remaining farmers go to farming
        for j in range(idx, F):
            environment.assign_group(farmers[j], "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave: Warriors should attack, Farmers should return to the Village
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```