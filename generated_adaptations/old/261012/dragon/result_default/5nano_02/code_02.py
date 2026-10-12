from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Assign villagers in the Village to:
        - farm: stay in Village and farm
        - cave: go to the Cave (not used here for Warriors, but defined)
        - spawn farmer: for every two villagers assigned here and 10 wheat, spawn a new Farmer
        - spawn warrior: not used in this strategy to honor "All Warriors should go to the Cave" rule
        """
        # Split villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Decide which farmers go to spawning and which go to farming
        spawn_farmers = []
        remaining_farmers = []

        # If we have at least two farmers and enough wheat, enable a small spawn setup
        if len(farmers) >= 2 and getattr(environment.farm, "wheat", 0) >= 10:
            spawn_farmers = farmers[:2]
            remaining_farmers = farmers[2:]
        else:
            remaining_farmers = farmers

        # Assign groups
        for c in spawn_farmers:
            environment.assign_group(c, "spawn farmer")

        for c in remaining_farmers:
            environment.assign_group(c, "farm")

        # All Warriors go to the Cave to attack
        for c in warriors:
            environment.assign_group(c, "cave")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Assign villagers in the Cave to:
        - attack: Warriors should attack the Dragon
        - cave: stay in Cave (not used by our strategy)
        - village: Farmers should return to the Village
        """
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                # Farmers go back to the Village to farm or spawn
                environment.assign_group(c, "village")