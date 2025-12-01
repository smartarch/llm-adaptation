from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Wheat available in the Farm
        wheat = getattr(environment.farm, "wheat", 0)

        # Decide non-overlapping farmers for spawning
        spawn_farmer = []
        spawn_warrior = []
        if len(farmers) >= 2 and wheat >= 10:
            spawn_farmer = [farmers[0], farmers[1]]
        if len(farmers) >= 4 and wheat >= 12:
            spawn_warrior = [farmers[2], farmers[3]]

        # Assign groups for farmers (ensuring exactly one group per farmer)
        for f in farmers:
            if f in spawn_farmer:
                environment.assign_group(f, "spawn farmer")
            elif f in spawn_warrior:
                environment.assign_group(f, "spawn warrior")
            else:
                environment.assign_group(f, "farm")

        # All Warriors should go to the Cave
        for w in warriors:
            environment.assign_group(w, "cave")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave: Warriors should attack; Farmers should return to Village
        for v in components:
            if getattr(v, "role", None) == "Warrior":
                environment.assign_group(v, "attack")
            else:
                environment.assign_group(v, "village")