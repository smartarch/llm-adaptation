from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Divide Villagers in the Village into:
        - farm: Stay in Village and farm
        - cave: Go to the Cave
        - spawn farmer: For every two villagers assigned to this group and 10 wheat, a new Farmer is spawned
        - spawn warrior: For every two villagers assigned to this group and 12 wheat, a new Warrior is spawned
        """
        # Separate villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # 1) Move all Warriors to the Cave
        for w in warriors:
            environment.assign_group(w, "cave")

        # 2) Assign Farmers with a single-pass strategy (to avoid repeated assignments)
        if not farmers:
            return

        total_wheat = getattr(getattr(environment, "farm", None), "wheat", 0)

        # Case A: spawn both farmer and warrior, if enough farmers and wheat
        if len(farmers) >= 4 and total_wheat >= 22:
            # First 2 -> spawn farmer
            for c in farmers[:2]:
                environment.assign_group(c, "spawn farmer")
            # Next 2 -> spawn warrior
            for c in farmers[2:4]:
                environment.assign_group(c, "spawn warrior")
            # Remaining farmers (if any) stay in farm
            for c in farmers[4:]:
                environment.assign_group(c, "farm")

        # Case B: only spawn farmer if enough wheat and at least 2 farmers
        elif len(farmers) >= 2 and total_wheat >= 10:
            # First 2 -> spawn farmer
            for c in farmers[:2]:
                environment.assign_group(c, "spawn farmer")
            # Remaining farmers stay in farm
            for c in farmers[2:]:
                environment.assign_group(c, "farm")

        # Case C: not enough wheat or not enough farmers - all stay farming
        else:
            for c in farmers:
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Divide Villagers in the Cave into:
        - attack: Attack the Dragon (Warriors should go here)
        - cave: Stay in the Cave
        - village: Go to the Village
        """
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            elif getattr(c, "role", None) == "Farmer":
                environment.assign_group(c, "village")