import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step):
        # Split by role — straightforward, no hidden failures.
        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        # Every warrior in the village must go to the cave immediately.
        for w in warriors:
            environment.assign_group(w, "cave")

        # Farmers: at least 2 must farm to produce wheat.
        # If we have 4 or more farmers, dedicate a pair to spawning a warrior.
        if len(farmers) >= 4:
            # 2 farmers → spawn warrior, all remaining farmers → farm.
            environment.assign_group(farmers[0], "spawn warrior")
            environment.assign_group(farmers[1], "spawn warrior")
            for f in farmers[2:]:
                environment.assign_group(f, "farm")
        else:
            # Too few farmers to risk a spawn; everyone farms.
            for f in farmers:
                environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        # Every warrior in the cave attacks, no exceptions.
        # Any non-warrior (a stray farmer) is sent back to the village.
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")