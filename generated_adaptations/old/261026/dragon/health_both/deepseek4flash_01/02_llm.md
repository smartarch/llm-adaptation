The adaptation strategy uses a clear priority system to balance economy and combat. In the Village, all Warriors are immediately sent to the Cave. Farmers are assigned to spawn new villagers: the first two spawns are Farmers to increase wheat production, after which all available wheat is spent on spawning Warriors to deal damage. Any remaining Farmers work on the farm. In the Cave, all Warriors are assigned to attack the Dragon, while any Farmers that end up there are sent back to the Village. This ensures that the Dragon is attacked early (Warriors enter the Cave on step 0 and attack from step 1), that all Warriors stay in the Cave attacking, that all Farmers remain in the Village, and that at least a few new Farmers and Warriors are spawned.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.spawned_farmers = 0
        self.spawned_warriors = 0

    def assign_in_village(self, components, environment, group_ids, step: int):
        farmers = []
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "cave")
            else:
                farmers.append(c)
        
        wheat = environment.farm.wheat
        
        # Spawn at least two new farmers first to boost wheat production
        if len(farmers) >= 2 and wheat >= 10 and self.spawned_farmers < 2:
            for f in farmers[:2]:
                environment.assign_group(f, "spawn farmer")
            self.spawned_farmers += 1
            for f in farmers[2:]:
                environment.assign_group(f, "farm")
        # Then spawn warriors whenever possible to increase damage
        elif len(farmers) >= 2 and wheat >= 12:
            for f in farmers[:2]:
                environment.assign_group(f, "spawn warrior")
            self.spawned_warriors += 1
            for f in farmers[2:]:
                environment.assign_group(f, "farm")
        else:
            for f in farmers:
                environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```