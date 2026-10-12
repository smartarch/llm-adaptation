from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Divide Villagers in the Village into:
        - farm: stay in Village and farm
        - cave: go to the Cave (will be re-assigned to attack in assign_in_cave)
        - spawn farmer: for every two villagers assigned to this group and 10 wheat, spawn a Farmer
        - spawn warrior: for every two villagers assigned to this group and 12 wheat, spawn a Warrior
        """
        # Collect farmers and warriors
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Prepare single-pass assignment mapping
        assignment = {}

        # 1) Warriors go to cave (they will attack later)
        for w in warriors:
            assignment[w] = "cave"

        # 2) Farmers default to farming
        for f in farmers:
            assignment[f] = "farm"

        # 3) Wheat available in farm (guard against missing attribute)
        wheat = 0
        farm_obj = getattr(environment, "farm", None)
        if farm_obj is not None:
            wheat = getattr(farm_obj, "wheat", 0)

        # 4) Attempt spawning decisions (single-pass, non-overlapping)
        # If we have at least 4 farmers and enough wheat, allocate two to spawn a farmer
        if len(farmers) >= 4 and wheat >= 10:
            to_spawn_farm = farmers[:2]
            for f in to_spawn_farm:
                assignment[f] = "spawn farmer"

            # Remaining farmers (at least 2) may spawn a warrior if wheat allows
            remaining = [f for f in farmers if f not in to_spawn_farm]
            if len(remaining) >= 2 and wheat >= 22:
                to_spawn_war = remaining[:2]
                for f in to_spawn_war:
                    assignment[f] = "spawn warrior"

        # If we couldn't spawn farmer but we can spawn a warrior using 4 farmers total
        elif len(farmers) >= 4 and wheat >= 12:
            remaining = farmers[:4]
            to_spawn_war = remaining[:2]
            for f in to_spawn_war:
                assignment[f] = "spawn warrior"

        # Apply the single-pass assignments
        for comp, grp in assignment.items():
            environment.assign_group(comp, grp)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Divide Villagers in the Cave into:
        - attack: Attack the Dragon (Warriors)
        - cave: Stay in the Cave
        - village: Go to the Village
        """
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")