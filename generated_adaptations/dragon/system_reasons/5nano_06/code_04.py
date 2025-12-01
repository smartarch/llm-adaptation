from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Divide Villagers in the Village into:
        - farm: stay in Village and farm
        - cave: go to the Cave
        - spawn farmer: for every two villagers assigned to this group and 10 wheat, a new Farmer is spawned
        - spawn warrior: for every two villagers assigned to this group and 12 wheat, a new Warrior is spawned
        """
        # Separate villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # 1) Move all Warriors to the Cave
        for w in warriors:
            environment.assign_group(w, "cave")

        # 2) Assign Farmers without re-assigning the same villager multiple times
        # Start by keeping all farmers in the farm, but opportunistically
        # allocate some to spawn groups if wheat allows.
        unassigned_farmers = list(farmers)

        # Current wheat available
        wheat = getattr(getattr(environment, "farm", None), "wheat", 0)

        # If possible, designate two Farmers to spawn another Farmer
        if len(unassigned_farmers) >= 2 and wheat >= 10:
            for c in unassigned_farmers[:2]:
                environment.assign_group(c, "spawn farmer")
            unassigned_farmers = unassigned_farmers[2:]

        # If possible, designate two more Farmers to spawn Warriors (using remaining farmers)
        if len(unassigned_farmers) >= 2 and wheat >= 12:
            for c in unassigned_farmers[:2]:
                environment.assign_group(c, "spawn warrior")
            unassigned_farmers = unassigned_farmers[2:]

        # The rest of the Farmers stay in the Farm group (in Village)
        for c in unassigned_farmers:
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