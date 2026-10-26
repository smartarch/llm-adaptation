The strategy sends every Warrior from the Village to the Cave immediately and assigns every Warrior there to attack on every step. Farmers stay in the Village, where pairs are temporarily assigned to spawning groups until two Farmers and two Warriors have been spawned; the remaining Farmers farm. Warrior spawning is prioritized because it increases Dragon damage. Every component is explicitly assigned on every callback, including those continuing their current action.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.spawned_farmers = 0
        self.spawned_warriors = 0

    @staticmethod
    def _group_ids(group_ids):
        # Use the provided valid names rather than assuming any group ordering.
        return {name: name for name in group_ids}

    def assign_in_village(self, components, environment, group_ids, step: int):
        groups = self._group_ids(group_ids)
        farmers = []

        for component in components:
            if component.role == "Warrior":
                environment.assign_group(component, groups["cave"])
            else:
                farmers.append(component)

        wheat = environment.farm.wheat
        spawn_name = None
        cost = 0

        # Spawn warriors first to increase Dragon damage, while also pursuing
        # the requested minimum of two spawns of each type.
        if self.spawned_warriors < 2 and wheat >= 12:
            spawn_name = "spawn warrior"
            cost = 12
        elif self.spawned_farmers < 2 and wheat >= 10:
            spawn_name = "spawn farmer"
            cost = 10

        if spawn_name is not None and len(farmers) >= 2:
            for component in farmers[:2]:
                environment.assign_group(component, groups[spawn_name])
            farmers = farmers[2:]

            # Each qualifying pair is assigned once as a spawn attempt.
            if spawn_name == "spawn warrior":
                self.spawned_warriors += 1
            else:
                self.spawned_farmers += 1

        for component in farmers:
            environment.assign_group(component, groups["farm"])

    def assign_in_cave(self, components, environment, group_ids, step: int):
        groups = self._group_ids(group_ids)

        for component in components:
            if component.role == "Warrior":
                environment.assign_group(component, groups["attack"])
            else:
                # Farmers contribute more by returning to work in the Village.
                environment.assign_group(component, groups["village"])
```