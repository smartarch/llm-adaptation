from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Default: Farmers stay in Village farming; Warriors go to Cave to prepare attack
        for f in farmers:
            environment.assign_group(f, "farm")
        for w in warriors:
            environment.assign_group(w, "cave")

        # Try to spawn new villagers based on wheat in the Farm
        wheat = getattr(environment.farm, "wheat", 0)

        # Spawn two new Farmers if possible (requires 2 farmers and at least 10 wheat)
        if len(farmers) >= 2 and wheat >= 10:
            # Reassign first two farmers to spawn farmer group
            environment.assign_group(farmers[0], "spawn farmer")
            environment.assign_group(farmers[1], "spawn farmer")

        # Spawn two new Warriors if possible (requires 4 farmers total and at least 12 wheat)
        # This uses two more farmers (indices 2 and 3) to spawn a Warrior
        if len(farmers) >= 4 and wheat >= 12:
            environment.assign_group(farmers[2], "spawn warrior")
            environment.assign_group(farmers[3], "spawn warrior")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave: Warriors should attack; Farmers should return to Village
        for v in components:
            if getattr(v, "role", None) == "Warrior":
                environment.assign_group(v, "attack")
            else:
                environment.assign_group(v, "village")