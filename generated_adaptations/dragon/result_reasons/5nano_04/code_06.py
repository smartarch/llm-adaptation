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

        # Spawn as many Warriors as possible this step, bounded to 2,
        # and only if we have enough Farmers to sacrifice (2 farmers per Warrior)
        max_possible_warrior_spawns = min(len(farmers) // 2, wheat // 12, 2)
        s_warrior = max_possible_warrior_spawns

        # After allocating Warrior spawns, recompute remaining farmers and wheat
        remaining_farmers = len(farmers) - 2 * s_warrior
        wheat_left_after_warriors = wheat - 12 * s_warrior

        # Spawn up to 2 Farmers this step if possible
        max_possible_farm_spawns = min(remaining_farmers // 2, wheat_left_after_warriors // 10, 2)
        s_farm = max_possible_farm_spawns

        # Assign specific farmers to groups
        idx = 0
        # First 2*s_warrior farmers -> "spawn warrior"
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

        # Warriors are already in the cave; no explicit movement needed here.

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave, decide who attacks and who stays
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                # Warriors should attack the Dragon
                environment.assign_group(c, "attack")
            else:
                # Farmers should go back to the Village
                environment.assign_group(c, "village")