from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Deterministic and robust village assignment:
        - Warriors -> cave (to move to the Cave and attack)
        - Non-Warriors (Farmers or others) -> farm (stay in Village)
        """
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "cave")
            else:
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Deterministic and robust cave assignment:
        - Warriors -> attack (attack the Dragon)
        - Non-Warriors -> village (return to the Village)
        """
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")