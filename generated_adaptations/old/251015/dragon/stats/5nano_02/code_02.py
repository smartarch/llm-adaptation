from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Move all Warriors in the Village to the Cave to prepare for attack
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "cave")

        # Collect Farmers and split them into farm / spawn groups deterministically
        farmers = [c for c in components if c.role == "Farmer"]

        for idx, f in enumerate(farmers):
            if idx < 2:
                environment.assign_group(f, "spawn farmer")
            elif idx < 4:
                environment.assign_group(f, "spawn warrior")
            else:
                environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave, send Warriors to attack the Dragon; Farmers return to Village
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")