from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Assign villagers in the Village into:
        - farm: Farmers stay in the Village to farm
        - cave: Warriors go to the Cave
        - spawn farmer: allocate some Farmers to enable spawning of new Farmers
        - spawn warrior: allocate some Farmers to enable spawning of new Warriors
        """
        # Separate by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Default moves
        to_farm = []
        to_spawn_farmer = []
        to_spawn_warrior = []
        to_cave = []

        # All Warriors should head to the Cave to attack
        to_cave.extend(warriors)

        # Farmers stay in Village by default
        remaining_farmers = list(farmers)

        # Wheat available for spawning logic
        wheat = getattr(getattr(environment, "farm", None), "wheat", 0)

        # Try to spawn farmers if possible (need >=2 farmers and >=10 wheat)
        if len(remaining_farmers) >= 2 and wheat >= 10:
            to_spawn_farmer = remaining_farmers[:2]
            remaining_farmers = remaining_farmers[2:]
        # Try to spawn warriors if possible (need >=2 farmers remaining and >=12 wheat)
        if len(remaining_farmers) >= 2 and wheat >= 12:
            to_spawn_warrior = remaining_farmers[:2]
            remaining_farmers = remaining_farmers[2:]

        # The rest stay in farm
        to_farm = remaining_farmers

        # Assign groups
        for c in to_farm:
            environment.assign_group(c, "farm")
        for c in to_spawn_farmer:
            environment.assign_group(c, "spawn farmer")
        for c in to_spawn_warrior:
            environment.assign_group(c, "spawn warrior")
        for c in to_cave:
            environment.assign_group(c, "cave")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Assign villagers in the Cave into:
        - attack: Warriors attack the Dragon
        - cave: Stay in the Cave (not used in this strategy, but kept for completeness)
        - village: Go to the Village
        """
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                # Farmers go back to the Village
                environment.assign_group(c, "village")