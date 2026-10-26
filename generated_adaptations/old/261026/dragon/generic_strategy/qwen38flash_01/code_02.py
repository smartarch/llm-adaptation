import math
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.spawned_warriors = 0
        self.spawned_farmers = 0

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat

        # Separate warriors and farmers
        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        # All warriors go to the cave to attack the dragon
        for w in warriors:
            environment.assign_group(w, "cave")

        # Handle farmer assignments
        remaining_farmers = list(farmers)

        # Spawn warriors first (they deal more damage) - need 2 villagers + 12 wheat
        while self.spawned_warriors < 2 and len(remaining_farmers) >= 2 and wheat >= 12:
            for _ in range(2):
                environment.assign_group(remaining_farmers.pop(0), "spawn warrior")
            wheat -= 12
            self.spawned_warriors += 1

        # Then spawn farmers (need 2 villagers + 10 wheat)
        while self.spawned_farmers < 2 and len(remaining_farmers) >= 2 and wheat >= 10:
            for _ in range(2):
                environment.assign_group(remaining_farmers.pop(0), "spawn farmer")
            wheat -= 10
            self.spawned_farmers += 1

        # All remaining farmers go to farm to produce wheat
        for f in remaining_farmers:
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.role == "Warrior":
                # Warriors stay in cave and attack the dragon
                environment.assign_group(c, "attack")
            elif c.role == "Farmer":
                # Farmers should not be in the cave; send them back to village
                environment.assign_group(c, "village")