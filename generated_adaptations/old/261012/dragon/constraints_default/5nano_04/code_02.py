from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate villagers by role
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # 1) All Warriors should go to the Cave
        for c in warriors:
            environment.assign_group(c, "cave")

        # 2) Spawn logic for Farmers (in the Village)
        if farmers:
            # Work with a copy for processing
            unassigned = farmers[:]
            wheat = environment.farm.wheat
            i = 0

            # Spawn Farmers in pairs if enough wheat (10)
            while i + 1 < len(unassigned) and wheat >= 10:
                environment.assign_group(unassigned[i], "spawn farmer")
                environment.assign_group(unassigned[i + 1], "spawn farmer")
                i += 2
                wheat -= 10

            # If still possible, spawn Warriors in pairs if enough wheat (12)
            while i + 1 < len(unassigned) and wheat >= 12:
                environment.assign_group(unassigned[i], "spawn warrior")
                environment.assign_group(unassigned[i + 1], "spawn warrior")
                i += 2
                wheat -= 12

            # Remaining farmers go farming
            for j in range(i, len(unassigned)):
                environment.assign_group(unassigned[j], "farm")

        # Done with village assignments
        return

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave: Warriors attack the Dragon; Farmers return to Village
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")