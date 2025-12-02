"""
SmartAdaptation v9: adaptive, budgeted spawning with HP-aware ramping

Rationale:
- Always send all Warriors to the Cave to attack the Dragon.
- Farmers are the Wheat engine. Spawning costs and the need to keep Wheat flowing require careful budgeting.
- Spawn events require 2 villagers in the target spawn group and a Wheat cost (10 for spawn farmer, 12 for spawn warrior).
- To win faster, spawn farmers aggressively but ensure at least one farmer remains in the Village to keep Wheat production. Then opportunistically spawn warriors when Wheat is available and the Dragon's HP or game step justifies a DPS push.
- Dragon HP awareness is used to gate Warrior spawns so we don't deplete Wheat too early while the Dragon is still strong.

Strategy details:
- In assign_in_village:
  - Move all Warriors to the Cave.
  - Compute max_farm_spawn_events = min(F // 2, Wheat // 10). Ensure we leave at least one Farmer farming by reducing events if all farmers would be consumed by spawns.
  - After allocating farm spawns, compute remaining_farmers and Wheat.
  - Compute max_war_spawn_events based on Dragon HP (<=30) or late steps (step >= 6). Use remaining Wheat and remaining Farmers.
  - Assign exactly 2*max_farm_spawn_events Farmers to "spawn farmer".
  - Assign exactly 2*max_war_spawn_events Farmers to "spawn warrior".
  - Remaining Farmers go to "farm".
- In assign_in_cave:
  - Warriors -> "attack"; Farmers -> "village".

This approach aims to maximize early Wheat growth while enabling a measured DPS ramp as soon as the Dragon becomes vulnerable, reducing overall steps to kill.

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

        # Wheat available at the Farm
        wheat = 0
        if hasattr(environment, "farm") and hasattr(environment.farm, "wheat"):
            wheat = environment.farm.wheat

        # Dragon health (if observable)
        dragon_hp = None
        if hasattr(environment, "dragon") and hasattr(environment.dragon, "hp"):
            dragon_hp = environment.dragon.hp

        # 1) Move all Warriors to the Cave (attack)
        for w in warriors:
            environment.assign_group(w, "cave")

        # 2) Aggressively spawn farmers: 2 farmers per event, cost 10 Wheat
        max_farm_spawn_events = min(F // 2, wheat // 10)
        # Ensure at least one farmer remains farming this step to sustain Wheat production
        if F - 2 * max_farm_spawn_events < 1 and max_farm_spawn_events > 0:
            max_farm_spawn_events -= 1

        to_spawn_farmers = max_farm_spawn_events * 2

        idx = 0
        for _ in range(to_spawn_farmers):
            if idx < F:
                environment.assign_group(farmers[idx], "spawn farmer")
                idx += 1

        # 3) Aggressively spawn warriors with remaining farmers and Wheat
        remaining_farmers = F - to_spawn_farmers
        wheat_after_farm = max(0, wheat - max_farm_spawn_events * 10)

        max_war_spawn_events = 0
        if dragon_hp is not None and dragon_hp <= 30:
            max_war_spawn_events = min(remaining_farmers // 2, wheat_after_farm // 12)
        elif step >= 6:
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