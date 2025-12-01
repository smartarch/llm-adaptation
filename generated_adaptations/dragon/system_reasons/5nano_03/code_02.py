from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Split villagers in village into Farmers and Warriors
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Decide farming vs spawning allocations for Farmers
        farm_to_place = 0
        if len(farmers) > 0:
            farm_to_place = max(1, int(len(farmers) * 0.6))
            if farm_to_place > len(farmers):
                farm_to_place = len(farmers)

        remaining = len(farmers) - farm_to_place
        farm_wheat = getattr(environment.farm, "wheat", 0)

        spawn_farmer = 0
        spawn_warrior = 0

        # Attempt to allocate spawns if wheat allows
        if remaining >= 2 and farm_wheat >= 10:
            spawn_farmer = min(2, remaining)
            remaining -= spawn_farmer
        if remaining >= 2 and farm_wheat >= 22:
            # If we have enough wheat left, spawn two warriors as well
            spawn_warrior = min(2, remaining)

        # Build index sets to assign groups deterministically
        farm_indices = set(range(0, farm_to_place))
        spawn_farmer_indices = set(range(farm_to_place, farm_to_place + spawn_farmer))
        spawn_warrior_indices = set(range(farm_to_place + spawn_farmer,
                                         farm_to_place + spawn_farmer + spawn_warrior))

        # Assign Farmers to their respective groups
        for idx, farmer in enumerate(farmers):
            if idx in farm_indices:
                group = "farm"
            elif idx in spawn_farmer_indices:
                group = "spawn farmer"
            elif idx in spawn_warrior_indices:
                group = "spawn warrior"
            else:
                # Fallback: keep in farm
                group = "farm"
            environment.assign_group(farmer, group)

        # All Warriors go to the Cave to prepare for attack
        for w in warriors:
            environment.assign_group(w, "cave")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the cave, send Warriors to attack and bring Farmers back to Village
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                # Farmers return to the Village
                environment.assign_group(c, "village")