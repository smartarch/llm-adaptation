from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Strategy:
        # - Move all Warriors to the Cave to head to the Dragon.
        # - Keep Farmers in the Village by default (farm group) to maximize wheat production.
        # - Use spawn groups to create new villagers based on current wheat.
        # - Spawn farmers when wheat >= 10 and there are at least 2 farmers (spawn farmer).
        # - Spawn warriors when wheat >= 12 and there are at least 4 farmers total (spawn warrior).
        if not components:
            return

        # Separate villagers by role
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # 1) Move all Warriors to the cave
        for c in warriors:
            environment.assign_group(c, "cave")

        # 2) Keep Farmers in the Village (default farming)
        for c in farmers:
            environment.assign_group(c, "farm")

        # Wheat available right now
        wheat = getattr(environment.farm, "wheat", 0)

        # 3) Spawn farmers if possible: needs 10 wheat and at least 2 farmers
        remaining_for_warrior_pool = list(farmers)  # copy
        if wheat >= 10 and len(remaining_for_warrior_pool) >= 2:
            f1, f2 = remaining_for_warrior_pool[0], remaining_for_warrior_pool[1]
            environment.assign_group(f1, "spawn farmer")
            environment.assign_group(f2, "spawn farmer")
            # Remove spawned farmers from pool for potential warrior spawn in this step
            remaining_for_warrior_pool = remaining_for_warrior_pool[2:]
        else:
            # not spawning farmers this step
            remaining_for_warrior_pool = remaining_for_warrior_pool

        # 4) Spawn warriors if possible: needs 12 wheat and at least 2 more farmers left
        if wheat >= 12 and len(remaining_for_warrior_pool) >= 2:
            s1, s2 = remaining_for_warrior_pool[0], remaining_for_warrior_pool[1]
            environment.assign_group(s1, "spawn warrior")
            environment.assign_group(s2, "spawn warrior")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave:
        # - All Warriors should attack (group "attack").
        # - All Farmers should go back to the Village (group "village").
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")