from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Divide villagers in village into groups:
        # - Warriors -> cave (to go to Cave and attack later)
        # - Farmers -> farm / spawn groups (spawn decisions depend on wheat)

        # Separate by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Spawn planning based on wheat and number of farmers available
        wheat = getattr(environment.farm, "wheat", 0)

        # We'll prepare a map from member -> target group
        target_group = {}

        # First, assign all Warriors in village to go to cave (to be attacked later in assign_in_cave)
        for w in warriors:
            target_group[w] = "cave"

        # Now plan spawn allocations for Farmers
        # Helper: we need to allocate at least 2 farmers to a spawn group to trigger a spawn.
        # We'll try the most aggressive plan first if possible.
        if wheat >= 22 and len(farmers) >= 4:
            # Spawn 2 farmers (spawn farmer) and 2 warriors (spawn warrior)
            for i, f in enumerate(farmers[:2]):
                target_group[f] = "spawn farmer"
            for i, f in enumerate(farmers[2:4]):
                target_group[f] = "spawn warrior"
            # Remaining farmers (if any) go to farm
            for f in farmers[4:]:
                target_group[f] = "farm"
        elif wheat >= 12 and len(farmers) >= 2:
            # Spawn 1 Warrior (spawn warrior) using 2 farmers
            for i, f in enumerate(farmers[:2]):
                target_group[f] = "spawn warrior"
            # Remaining farmers (if any) go to farm
            for f in farmers[2:]:
                target_group[f] = "farm"
        elif wheat >= 10 and len(farmers) >= 2:
            # Spawn 1 Farmer (spawn farmer) using 2 farmers
            for i, f in enumerate(farmers[:2]):
                target_group[f] = "spawn farmer"
            # Remaining farmers (if any) go to farm
            for f in farmers[2:]:
                target_group[f] = "farm"
        else:
            # No spawning this step; all farmers stay and farm
            for f in farmers:
                target_group[f] = "farm"

        # If there were farmers not mentioned (shouldn't happen), assign to farm
        for f in farmers:
            if f not in target_group:
                target_group[f] = "farm"

        # Now apply assignments
        for comp, gid in target_group.items():
            environment.assign_group(comp, gid)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In cave, make Warriors attack and move Farmers back to Village
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            elif role == "Farmer":
                # Farmers should go to Village
                environment.assign_group(c, "village")
            else:
                # Fallback: keep in cave if unknown role
                environment.assign_group(c, "cave")