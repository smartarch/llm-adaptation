from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Classify villagers in the Village
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Default: Farmers stay in Village as 'farm', Warriors go to Cave as 'cave'
        for c in farmers:
            environment.assign_group(c, "farm")
        for c in warriors:
            environment.assign_group(c, "cave")

        # Attempt spawning based on available wheat and number of farmers
        wheat = getattr(environment.farm, "wheat", 0)

        # Case 1: If we have enough farmers and wheat to seed both a farmer and a warrior
        if len(farmers) >= 4 and wheat >= 22:
            # Use first two farmers to spawn a Farmer, next two to spawn a Warrior
            for c in farmers[:2]:
                environment.assign_group(c, "spawn farmer")
            for c in farmers[2:4]:
                environment.assign_group(c, "spawn warrior")

        # Case 2: If we don't have enough for both, try to spawn at least one Farmer
        elif len(farmers) >= 2 and wheat >= 10:
            # Use first two farmers to spawn a Farmer
            for c in farmers[:2]:
                environment.assign_group(c, "spawn farmer")

        # If there are no spawns possible, farmers remain in 'farm' and Warriors in 'cave'
        # The environment will handle the actual spawning based on these group assignments.

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave: all Warriors should attack the Dragon; Farmers should return to Village
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")