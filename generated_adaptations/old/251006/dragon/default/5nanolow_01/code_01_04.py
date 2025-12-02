import abc

from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Partition villagers into final groups with a single assignment per component.
        farmers = []
        warriors = []

        for c in components:
            if getattr(c, "role", None) == "Farmer":
                farmers.append(c)
            elif getattr(c, "role", None) == "Warrior":
                warriors.append(c)

        # Gather wheat available for spawning (per problem statement, from farm)
        wheat = 0
        try:
            wheat = int(getattr(environment.farm, "wheat", 0))
        except Exception:
            wheat = 0

        # Decide spawn farmer capacity: 2 villagers per pair, needs 10 wheat per pair
        max_pairs_farmers = 0
        if wheat >= 10:
            max_pairs_farmers = min(len(farmers) // 2, wheat // 10)
        spawn_farmers = 2 * max_pairs_farmers

        # Wheat remaining after farmer-spawns
        wheat_after_farm_spawns = wheat - (spawn_farmers * 10)

        # Decide spawn warrior capacity: 2 villagers per pair, needs 12 wheat per pair
        max_pairs_warriors = 0
        if wheat_after_farm_spawns >= 12:
            max_pairs_warriors = min(len(warriors) // 2, wheat_after_farm_spawns // 12)
        spawn_warriors = 2 * max_pairs_warriors

        # Assign final groups (single assignment per component)
        # First, those designated to spawn groups
        for i, f in enumerate(farmers):
            if i < spawn_farmers:
                environment.assign_group(f, "spawn farmer")
            else:
                environment.assign_group(f, "farm")

        for i, w in enumerate(warriors):
            if i < spawn_warriors:
                environment.assign_group(w, "spawn warrior")
            else:
                # Warriors not spawning go to cave (to attack)
                environment.assign_group(w, "cave")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the cave, assign all Warriors to attack, others to cave (or keep them in cave)
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "cave")