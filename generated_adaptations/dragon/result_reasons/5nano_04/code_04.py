from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Strategy: All Warriors should go to the Cave (to attack later)
        for w in warriors:
            environment.assign_group(w, "cave")

        # Wheat available for spawning
        wheat = getattr(environment.farm, "wheat", 0)

        # How many spawns are possible given current numbers
        # We will cap spawns to at most 2 Warriors and at most 2 Farmers per step
        max_warrior_spawns = min(len(farmers) // 2, max(0, wheat // 12))
        max_farm_spawns = min((len(farmers) - 2 * max_warrior_spawns) // 2, max(0, (wheat - 12 * max_warrior_spawns) // 10))

        s_warrior = 0
        s_farm = 0

        # Early aggressive spawns (steps 1-6)
        if step <= 6 and max_warrior_spawns > 0:
            s_warrior = 1  # spawn up to one extra Warrior early

        # After potential warrior spawn, recompute available for farmers
        remaining_farmers_after_warrior = len(farmers) - 2 * s_warrior

        # Allow up to 2 farmer-spawns if possible
        if step <= 12 and remaining_farmers_after_warrior > 0 and max_farm_spawns > 0:
            s_farm = min(2, max_farm_spawns)

        # Ensure non-negative allocations
        s_warrior = max(0, s_warrior)
        s_farm = max(0, s_farm)

        # Assign specific farmers to groups
        # First 2*s_warrior farmers -> "spawn warrior"
        idx = 0
        farmers_to_spawn_warrior = farmers[idx: idx + 2 * s_warrior]
        idx += 2 * s_warrior

        # Next 2*s_farm farmers -> "spawn farmer"
        farmers_to_spawn_farm = farmers[idx: idx + 2 * s_farm]
        idx += 2 * s_farm

        # The remaining farmers stay in Farm (Village)
        farmers_to_farm = farmers[idx:]

        for f in farmers_to_spawn_warrior:
            environment.assign_group(f, "spawn warrior")
        for f in farmers_to_spawn_farm:
            environment.assign_group(f, "spawn farmer")
        for f in farmers_to_farm:
            environment.assign_group(f, "farm")

        # Warriors are already in cave; no explicit farmer should be moved to cave here.

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave, decide who attacks and who stays
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                # Warriors should attack the Dragon
                environment.assign_group(c, "attack")
            else:
                # Farmers should go back to the Village
                environment.assign_group(c, "village")