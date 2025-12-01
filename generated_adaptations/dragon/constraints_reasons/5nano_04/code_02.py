from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Classify villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Prepare a provisional assignment map
        assignment = {}

        # Default actions: Farmers stay in village to farm, Warriors go to cave
        for f in farmers:
            assignment[f] = "farm"
        for w in warriors:
            assignment[w] = "cave"

        # Spawn strategy:
        #  - Try to spawn two farmers if we have enough farmers to spare and we are still early (step <= 15)
        #  - Then try to spawn warriors if enough wheat is available and we still have farmers to spare
        if step <= 15 and len(farmers) >= 4:
            # Find those farmers currently in farming
            farming_left = [f for f in farmers if assignment.get(f) == "farm"]
            # Move up to 2 farmers to the spawn farmer group, leaving at least 2 farming
            to_move = min(2, max(0, len(farming_left) - 2))
            for i in range(to_move):
                assignment[farming_left[i]] = "spawn farmer"

        # Attempt to spawn warriors if wheat is available and we have enough farmers to spare
        if step <= 15 and getattr(environment.farm, "wheat", 0) >= 12:
            farming_left = [f for f in farmers if assignment.get(f) == "farm"]
            if len(farming_left) >= 2:
                for i in range(min(2, len(farming_left))):
                    assignment[farming_left[i]] = "spawn warrior"

        # Apply the determined group assignments
        for comp in components:
            group = assignment.get(comp, "farm")  # default to farm if not specified
            environment.assign_group(comp, group)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave: all Warriors should attack, Farmers should go back to the Village
        for comp in components:
            if getattr(comp, "role", None) == "Warrior":
                environment.assign_group(comp, "attack")
            else:
                environment.assign_group(comp, "village")