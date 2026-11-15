from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._spawned = {
            "spawn warrior": 0,
            "spawn farmer": 0,
        }

    @staticmethod
    def _role(component):
        return str(component.role).lower().split(".")[-1]

    @staticmethod
    def _assign(environment, component, group):
        environment.assign_group(component, group)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = max(0, environment.farm.wheat)
        assigned = set()
        farmers = []

        # A Warrior in the Village eats if hungry, then can return to the Cave
        # on a later turn. New, fed Warriors head directly to the Cave.
        for component in components:
            if self._role(component) == "warrior":
                if component.steps_since_meal > 0:
                    self._assign(environment, component, "eat")
                    assigned.add(id(component))
                    wheat = max(0, wheat - 1)
                else:
                    self._assign(environment, component, "cave")
                    assigned.add(id(component))
            else:
                farmers.append(component)

        # Farmers eat before reaching the starvation threshold.
        for component in farmers:
            if component.steps_since_meal >= 5 and wheat > 0:
                self._assign(environment, component, "eat")
                assigned.add(id(component))
                wheat -= 1

        # Reserve food for Farmers who are approaching their meal deadline.
        reserve = sum(
            1 for component in farmers
            if id(component) not in assigned
            and component.steps_since_meal >= 4
        )
        spawn_wheat = max(0, wheat - reserve)

        candidates = [
            component for component in farmers
            if id(component) not in assigned
        ]
        candidates.sort(
            key=lambda component: (component.steps_since_meal, -component.hp)
        )

        # Spawn in pairs, prioritizing Warriors for Dragon damage and then
        # spawning Farmers. Limit to one spawn group per turn so other Farmers
        # can continue farming or eating.
        if len(candidates) >= 2:
            outstanding = [
                name for name in ("spawn warrior", "spawn farmer")
                if self._spawned[name] < 2
            ]
            if outstanding:
                name = min(
                    outstanding,
                    key=lambda group: (
                        self._spawned[group],
                        0 if group == "spawn warrior" else 1,
                    ),
                )
                cost = 12 if name == "spawn warrior" else 10
                if spawn_wheat >= cost:
                    for component in candidates[:2]:
                        self._assign(environment, component, name)
                        assigned.add(id(component))
                    self._spawned[name] += 1

        # Explicitly assign all remaining components.
        for component in components:
            if id(component) in assigned:
                continue
            if self._role(component) == "warrior":
                self._assign(environment, component, "cave")
            else:
                self._assign(environment, component, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        warriors = []

        for component in components:
            if self._role(component) == "warrior":
                warriors.append(component)
            else:
                # Farmers belong in the Village.
                self._assign(environment, component, "village")

        if not warriors:
            return

        # Return one Warrior at a time for food, preserving Cave attackers
        # whenever there is more than one Warrior present.
        eligible = [
            component for component in warriors
            if component.steps_since_meal >= 4
        ]
        eligible.sort(
            key=lambda component: (
                -component.steps_since_meal,
                component.hp,
            )
        )

        returning = None
        if len(warriors) == 1:
            # A lone Warrior can keep attacking until it must return to eat.
            if warriors[0].steps_since_meal >= 5:
                returning = warriors[0]
        elif eligible:
            returning = eligible[0]

        for component in warriors:
            if component is returning:
                self._assign(environment, component, "village")
            else:
                self._assign(environment, component, "attack")