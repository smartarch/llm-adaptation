import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step):
        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        # Every warrior in the village must head to the cave right now.
        for w in warriors:
            environment.assign_group(w, "cave")

        # Farmers: greedily form warrior-spawn pairs; leftovers farm.
        # The engine will ignore the pair if wheat < 12, so we always try.
        num_pairs = len(farmers) // 2
        spawn_pool = farmers[: num_pairs * 2]
        leftover = farmers[num_pairs * 2:]

        for f in spawn_pool:
            environment.assign_group(f, "spawn warrior")
        for f in leftover:
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                # A farmer that ended up in the cave goes home.
                environment.assign_group(c, "village")