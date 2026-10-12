from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Divide Village villagers into:
        - farm: stay in Village and farm
        - cave: go to the Cave (to join attack later)
        - spawn farmer: for every two villagers assigned and 10 wheat, spawn a new Farmer
        - spawn warrior: for every two villagers assigned and 12 wheat, spawn a new Warrior
        """
        # Separate current villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        n_farmers = len(farmers)
        n_warriors = len(warriors)

        # Wheat available for spawning (from the Farm)
        wheat = 0
        farm = getattr(environment, "farm", None)
        if farm is not None:
            wheat_attr = getattr(farm, "wheat", None)
            if wheat_attr is not None:
                try:
                    wheat = int(wheat_attr)
                except (TypeError, ValueError):
                    wheat = 0

        # Spawning plan (as many as possible given wheat and farmer availability)
        # s_farm: number of 2-farmer groups we will assign to "spawn farmer"
        s_farm = min(n_farmers // 2, wheat // 10)

        remaining_farmers_after_farm_spawns = n_farmers - (2 * s_farm)

        # s_war: number of 2-farmer groups we will assign to "spawn warrior"
        # Ensure we have enough farmers left for these spawns and enough wheat left
        wheat_after_farm = wheat - (10 * s_farm)
        s_war = min(remaining_farmers_after_farm_spawns // 2, max(0, wheat_after_farm // 12))

        # Assign groups
        # First 2*s_farm farmers -> "spawn farmer"
        idx = 0
        for _ in range(2 * s_farm):
            environment.assign_group(farmers[idx], "spawn farmer")
            idx += 1

        # Next 2*s_war farmers -> "spawn warrior"
        for _ in range(2 * s_war):
            environment.assign_group(farmers[idx], "spawn warrior")
            idx += 1

        # Remaining farmers -> "farm" (stay in Village and farm)
        for i in range(idx, n_farmers):
            environment.assign_group(farmers[i], "farm")

        # All Warriors should go to the Cave (to join the attack)
        for w in warriors:
            environment.assign_group(w, "cave")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Divide Cave villagers into:
        - attack: Warriors attack the Dragon
        - cave: stay in cave (unused for Warriors in this strategy)
        - village: Farmers go back to Village
        """
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                # Warriors should attack the Dragon
                environment.assign_group(c, "attack")
            else:
                # Farmers go back to Village
                environment.assign_group(c, "village")