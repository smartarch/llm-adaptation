"""
SmartAdaptation v6: aggressive, greedy spawning to minimize steps

Rationale:
- Always maximize early offense: send all Warriors to the Cave to attack the Dragon as soon as possible.
- In the Village, spawn Farmers and Warriors as greedily as Wheat allows:
  - For every 2 Farmers assigned to "spawn farmer" and 10 Wheat, one new Farmer is spawned.
  - For every 2 Farmers assigned to "spawn warrior" and 12 Wheat, one new Warrior is spawned.
- This version removes per-step caps on spawns to aggressively ramp up Wheat production and DPS as soon as resources allow.
- Farmers remain essential for Wheat generation; Warriors directly amplify DPS. We keep Warriors in the Cave at all times.
- Assignments are explicit every step to ensure deterministic behavior.

Adaptation details:
- assign_in_village:
  - Move all Warriors to the Cave.
  - Compute maximum possible farmer-spawn events given current farmers and Wheat.
  - Deduct Wheat for those farmer spawns.
  - Compute maximum possible warrior-spawn events with remaining farmers and Wheat.
  - Assign 2*farm_spawn_events farmers to "spawn farmer".
  - Assign 2*war_spawn_events farmers to "spawn warrior".
  - Remaining farmers go to "farm".
- assign_in_cave:
  - Warriors go to "attack".
  - Farmers go to "village".

"""

from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        F = len(farmers)
        W = len(warriors)

        # Wheat available at the Farm (if present)
        wheat = 0
        if hasattr(environment, "farm") and hasattr(environment.farm, "wheat"):
            wheat = environment.farm.wheat

        # 1) Move all Warriors to Cave (to attack)
        for w in warriors:
            environment.assign_group(w, "cave")

        # 2) Spawn farmers as greedily as possible
        max_farm_spawn_events = min(F // 2, wheat // 10)
        to_spawn_farmers = max_farm_spawn_events * 2

        idx = 0
        for _ in range(to_spawn_farmers):
            if idx < F:
                environment.assign_group(farmers[idx], "spawn farmer")
                idx += 1

        # 3) Spawn warriors greedily with remaining farmers and wheat
        remaining_farmers = F - to_spawn_farmers // 2
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