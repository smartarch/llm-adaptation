import abc

from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Simple, stable strategy:
        # - Farmers stay in Village and farm
        # - Warriors go to Cave (to attack)
        # - Do not use spawn groups to keep a single assignment per component
        for c in components:
            role = getattr(c, "role", None)
            if role == "Farmer":
                environment.assign_group(c, "farm")
            elif role == "Warrior":
                environment.assign_group(c, "cave")
            else:
                # Fallback for any unexpected component types
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the cave, all Warriors should attack. Others stay in cave for safety.
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "cave")