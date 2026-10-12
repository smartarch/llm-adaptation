from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Classify villagers in the Village
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # We'll assign exactly one group per farmer.
        # Default: all farmers go to "farm"
        assign_map = {}

        for f in farmers:
            assign_map[f] = "farm"

        # All Warriors should go to the Cave (to be attacked later in cave phase)
        for w in warriors:
            environment.assign_group(w, "cave")

        # Read current wheat from the Farm
        wheat = getattr(environment.farm, "wheat", 0)

        # Spawn decision: try to spawn war or farmer, but keep assignments non-overlapping
        if len(farmers) >= 2 and wheat >= 12:
            # Use first two farmers to spawn a Warrior
            f1, f2 = farmers[0], farmers[1]
            assign_map[f1] = "spawn warrior"
            assign_map[f2] = "spawn warrior"
            # Remaining farmers (if any) stay on farm
        elif len(farmers) >= 2 and wheat >= 10:
            # Use first two farmers to spawn a Farmer
            f1, f2 = farmers[0], farmers[1]
            assign_map[f1] = "spawn farmer"
            assign_map[f2] = "spawn farmer"
            # Remaining farmers stay on farm
        # else: keep all farmers on farm (already in assign_map)

        # Apply final assignments (each farmer assigned exactly once)
        for c, grp in assign_map.items():
            environment.assign_group(c, grp)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave: all Warriors should attack the Dragon; Farmers should go to Village
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")