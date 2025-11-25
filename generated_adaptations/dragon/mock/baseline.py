"""All Warriors should go to the Cave, and then attack the Dragon. All Farmers should stay in Village and farm or spawn new villagers (both Farmers and Warriors are necessary)."""
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):

    def assign_in_village(self, components, environment, group_ids, step: int):
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]
        wheat = environment.farm.wheat

        # All Warriors should go to the Cave
        for c in warriors:
            environment.assign_group(c, "cave")

        if wheat >= 12 and len(farmers) >= 2:  # warrior spawn cost
            # spawn warrior
            environment.assign_group(farmers[0], "spawn warrior")
            environment.assign_group(farmers[1], "spawn warrior")
            farmers = farmers[2:]  # remove assigned farmers
            wheat -= 12

        if wheat >= 10 and len(farmers) >= 2:  # farmer spawn cost
            # spawn farmer
            environment.assign_group(farmers[0], "spawn farmer")
            environment.assign_group(farmers[1], "spawn farmer")
            farmers = farmers[2:]  # remove assigned farmers
            wheat -= 10

        # Remaining Farmers should farm
        for c in farmers:
            environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # All Warriors should attack the Dragon
        for c in components:
            environment.assign_group(c, "attack")
