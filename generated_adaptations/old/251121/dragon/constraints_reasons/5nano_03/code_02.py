import abc

from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Gather villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # 1) All Warriors go to the Cave (to reach the Cave)
        for c in warriors:
            environment.assign_group(c, "cave")

        # 2) Farmers stay in Village by default (group "farm")
        for c in farmers:
            environment.assign_group(c, "farm")

        # 3) Spawning strategy (spawn groups in Village)
        # We attempt to spawn as follows, based on available wheat:
        # - If at least 10 wheat and at least 2 farmers exist, assign 2 farmers to spawn farmer
        # - If at least 22 wheat and at least 4 farmers exist, assign 2 more farmers to spawn warrior
        farm_wheat = getattr(getattr(environment, "farm", None), "wheat", 0)

        # Helper: safe indexing
        num_farmers = len(farmers)

        if num_farmers >= 4 and farm_wheat >= 22:
            # Assign two to spawn farmer, two to spawn warrior
            environment.assign_group(farmers[0], "spawn farmer")
            environment.assign_group(farmers[1], "spawn farmer")
            environment.assign_group(farmers[2], "spawn warrior")
            environment.assign_group(farmers[3], "spawn warrior")
        elif num_farmers >= 2 and farm_wheat >= 10:
            # Assign two to spawn farmer
            environment.assign_group(farmers[0], "spawn farmer")
            environment.assign_group(farmers[1], "spawn farmer")
        # Remaining farmers stay in 'farm' (already assigned above)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave, all Warriors should attack; Farmers should go back to Village
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")