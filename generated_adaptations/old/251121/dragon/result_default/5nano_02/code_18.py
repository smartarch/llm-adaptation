"""
SmartAdaptation v8: robust budgeted spawns with per-step and dragon-health awareness

- Warriors -> Cave (attack) always.
- Farmers: spawn farmers as aggressively as possible given Wheat, but keep at least one farmer farming.
- Then spawn warriors if Wheat remains and conditions allow (HP-based or late-step triggers).
- Remaining farmers go to farming.
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
        # W = len(warriors)  # not used directly, kept for readability

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

        # 2) Aggressively spawn farmers: 2 Farmers per event, 10 Wheat per event
        max_farm_spawn_events = min(F // 2, wheat // 10)

        # Ensure at least one farmer remains farming this step to keep Wheat production
        # Adjust max_farm_spawn_events downward if needed
        while F - max_farm_spawn_events * 2 <= 0 and max_farm_spawn_events > 0:
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
        if (dragon_hp is not None and dragon_hp <= 25) or (step >= 15):
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