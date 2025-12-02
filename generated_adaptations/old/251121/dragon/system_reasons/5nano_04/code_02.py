from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Assign villagers in the Village to:
        - farm: Farmers stay and farm
        - cave: Warriors move to the Cave
        - spawn farmer: two villagers in this group will spawn a new Farmer (needs 10 wheat)
        - spawn warrior: two villagers in this group will spawn a new Warrior (needs 12 wheat)
        """
        # Defaults: Farmers -> farm, Warriors -> cave
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Move Warriors to cave; Farmers stay in village (farm)
        for w in warriors:
            environment.assign_group(w, "cave")
        for f in farmers:
            environment.assign_group(f, "farm")

        # Spawn strategy based on available wheat and number of farmers
        wheat = getattr(environment.farm, "wheat", 0)

        # Re-assign some farmers to spawn groups if we have enough wheat and enough farmers
        # We prioritize spawning multiple villagers when possible.
        if len(farmers) >= 4 and wheat >= 20:
            # First two farmers to spawn farmer, next two to spawn warrior
            environment.assign_group(farmers[0], "spawn farmer")
            environment.assign_group(farmers[1], "spawn farmer")
            environment.assign_group(farmers[2], "spawn warrior")
            environment.assign_group(farmers[3], "spawn warrior")
        elif len(farmers) >= 2 and wheat >= 12:
            # Spawn two Warriors from farmers
            environment.assign_group(farmers[0], "spawn warrior")
            environment.assign_group(farmers[1], "spawn warrior")
        elif len(farmers) >= 2 and wheat >= 10:
            # Spawn two Farmers from farmers
            environment.assign_group(farmers[0], "spawn farmer")
            environment.assign_group(farmers[1], "spawn farmer")
        # If none of the conditions apply, keep default assignments (farmers in farm, warriors in cave)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Assign villagers in the Cave to:
        - attack: Warriors attack the Dragon
        - cave: (stay in the Cave) - but to satisfy farmer requirement, Farmers go to village
        - village: Farmers go back to Village
        """
        # Warriors attack the Dragon; Farmers go back to Village
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                # Farmers should stay in the Village; move them back to Village
                environment.assign_group(c, "village")