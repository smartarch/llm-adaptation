from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Split villagers by role
        farmers = [c for c in components if getattr(c, "role", "") == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", "") == "Warrior"]

        # 1) All Warriors should go to the Cave (to attack)
        for w in warriors:
            environment.assign_group(w, "cave")

        # 2) Farmers stay in Village and farm or spawn new villagers
        #    We keep a simple adaptive distribution among farming, spawn farmer, spawn warrior.

        wheat = getattr(environment.farm, "wheat", 0)

        # If there are no farmers, nothing to allocate
        if not farmers:
            return

        # Heuristic allocation
        assign_farm = []
        assign_spawn_farmer = []
        assign_spawn_warrior = []

        nf = len(farmers)

        # Strategy Rules (simple greedy policy)
        # - If we have at least 4 farmers and high wheat, spawn both farmer and warrior (2 each)
        if nf >= 4 and wheat >= 22:
            assign_spawn_farmer = farmers[:2]
            assign_spawn_warrior = farmers[2:4]
            assign_farm = farmers[4:]
        # - If we have at least 3 farmers and some wheat, spawn a warrior (needs 2 villagers)
        elif nf >= 3 and wheat >= 12:
            assign_spawn_warrior = farmers[:2]
            assign_farm = farmers[2:]
        # - If we have at least 2 farmers and some wheat, spawn a farmer
        elif nf >= 2 and wheat >= 10:
            assign_spawn_farmer = farmers[:2]
            assign_farm = farmers[2:]
        # - Otherwise, just farm with all farmers
        else:
            assign_farm = farmers

        # Apply assignments
        for f in assign_farm:
            environment.assign_group(f, "farm")
        for f in assign_spawn_farmer:
            environment.assign_group(f, "spawn farmer")
        for f in assign_spawn_warrior:
            environment.assign_group(f, "spawn warrior")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the cave, send Warriors to attack, Farmers back to Village
        for c in components:
            if getattr(c, "role", "") == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")