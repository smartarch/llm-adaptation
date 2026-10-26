from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step):
        for c in components:
            environment.assign_group(c, "cave")

    def assign_in_cave(self, components, environment, group_ids, step):
        for c in components:
            environment.assign_group(c, "attack")