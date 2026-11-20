The previous policy stopped spawning after two warriors and returned Cave warriors in synchronized batches, leaving the Dragon unattacked for long stretches. This version keeps producing warriors when wheat allows, while retaining at least one farmer to replenish supplies. It prioritizes meals, sends hungry warriors home early, and explicitly assigns every villager each step. Since the available attributes do not identify newly spawned villagers, it tracks the initial farmer-spawn goal through assignments and continues spawning warriors whenever resources permit.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._farmer_spawn_requested = False

    @staticmethod
    def _role(component):
        return str(component.role).lower()

    @staticmethod
    def _hunger(component):
        return int(component.steps_since_meal)

    def assign_in_village(self, components, environment, group_ids, step: int):
        components = list(components)
        wheat = max(0, int(environment.farm.wheat))

        # Eat while there is still time to return to the Cave or avoid
        # starvation. Warriors eat at a lower hunger level because they need
        # time to travel back to the Cave afterward.
        due = [
            c for c in components
            if self._hunger(c) >= (4 if self._role(c) == "warrior" else 5)
        ]
        due.sort(key=lambda c: (self._hunger(c), -int(c.hp)), reverse=True)

        eaters = due[:wheat]
        eaten = {id(c) for c in eaters}
        wheat_left = wheat - len(eaters)

        actions = {}
        for c in components:
            if id(c) in eaten:
                actions[id(c)] = "eat"
            elif self._role(c) == "warrior" and self._hunger(c) < 4:
                actions[id(c)] = "cave"
            else:
                actions[id(c)] = "farm"

        # Spawn with farmers where possible, so warriors can head to the Cave.
        # Keep at least one farmer working whenever the group is large enough.
        farmers = [
            c for c in components
            if self._role(c) == "farmer" and id(c) not in eaten
        ]
        farmers.sort(key=lambda c: self._hunger(c))

        if not self._farmer_spawn_requested:
            # The required farmer is spawned once there is enough wheat for
            # the spawn and a modest meal reserve.
            if len(farmers) >= 2 and wheat_left >= 12:
                for c in farmers[:2]:
                    actions[id(c)] = "spawn farmer"
                self._farmer_spawn_requested = True
        else:
            # Replenish the attacking force whenever the food supply permits.
            # Leave one farmer to work when possible, and do not spend the
            # reserve needed for imminent meals.
            available = [
                c for c in farmers
                if actions[id(c)] == "farm"
            ]
            keep_farming = 1 if len(available) >= 3 else 0
            spawnable = available[:max(0, len(available) - keep_farming)]
            if len(spawnable) >= 2 and wheat_left >= 15:
                for c in spawnable[:2]:
                    actions[id(c)] = "spawn warrior"

        for c in components:
            environment.assign_group(c, actions[id(c)])

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if self._role(c) == "farmer":
                action = "village"
            elif self._hunger(c) >= 4:
                # One step to travel home, then eat before reaching the
                # starvation deadline.
                action = "village"
            else:
                action = "attack"

            environment.assign_group(c, action)
```