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

        # Warriors eat in the Village when needed; otherwise they head to Cave.
        for component in components:
            if self._role(component) == "warrior":
                if component.steps_since_meal >= 3:
                    self._assign(environment, component, "eat")
                    assigned.add(id(component))
                    wheat = max(0, wheat - 1)
                else:
                    self._assign(environment, component, "cave")
                    assigned.add(id(component))
            else:
                farmers.append(component)

        # Feed Farmers before the starvation deadline.
        for component in farmers:
            if component.steps_since_meal >= 5 and wheat > 0:
                self._assign(environment, component, "eat")
                assigned.add(id(component))
                wheat -= 1

        # Reserve wheat for Farmers who will need meals soon.
        meal_reserve = sum(
            1 for component in farmers
            if id(component) not in assigned
            and component.steps_since_meal >= 4
        )
        available_wheat = max(0, wheat - meal_reserve)

        # Prefer recently fed Farmers for spawning, leaving hungry Farmers
        # available to eat or work.
        candidates = [
            component for component in farmers
            if id(component) not in assigned
            and component.steps_since_meal < 4
        ]
        candidates.sort(
            key=lambda component: (
                component.steps_since_meal,
                -component.hp,
            )
        )

        # Keep two Farmers out of spawn groups when possible so food production
        # can continue. Complete the requested spawns first, then add Warriors.
        while len(candidates) >= 4:
            if self._spawned["spawn warrior"] < 2:
                spawn_group = "spawn warrior"
                cost = 12
            elif self._spawned["spawn farmer"] < 2:
                spawn_group = "spawn farmer"
                cost = 10
            else:
                spawn_group = "spawn warrior"
                cost = 12

            if available_wheat < cost:
                break

            pair = candidates[:2]
            candidates = candidates[2:]
            for component in pair:
                self._assign(environment, component, spawn_group)
                assigned.add(id(component))

            self._spawned[spawn_group] += 1
            available_wheat -= cost

        # Explicitly assign all remaining villagers.
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
                self._assign(environment, component, "village")

        if not warriors:
            return

        # Send the hungriest eligible Warrior back for food, while the others
        # keep attacking. Return at hunger 4 to allow travel before starvation.
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
        returning = eligible[0] if eligible else None

        for component in warriors:
            if component is returning:
                self._assign(environment, component, "village")
            else:
                self._assign(environment, component, "attack")