import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartDragonHuntAdaptation(DragonHuntAdaptation):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step):
        for c in components:
            role = str(getattr(c, "role", "")).lower()
            if role == "warrior":
                environment.assign_group(c, "cave")
            else:
                # Farmers: try to pair for spawn, else farm.
                # (Pairing logic handled after the loop.)
                pass

        farmers = [c for c in components
                   if str(getattr(c, "role", "")).lower() == "farmer"]

        # Greedy pairing: every two farmers → "spawn"; leftover → "farm"
        num_pairs = len(farmers) // 2
        for i in range(num_pairs * 2):
            environment.assign_group(farmers[i], "spawn")
        for i in range(num_pairs * 2, len(farmers)):
            environment.assign_group(farmers[i], "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        for c in components:
            role = str(getattr(c, "role", "")).lower()
            if role == "warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")