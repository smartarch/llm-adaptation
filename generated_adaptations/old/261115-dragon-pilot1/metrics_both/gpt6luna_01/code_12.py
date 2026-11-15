from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._spawned = {"spawn warrior": 0, "spawn farmer": 0}
        self._returning_for_food = set()

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

        for component in components:
            key = id(component)
            if self._role(component) == "warrior":
                hunger = component.steps_since_meal

                # Warriors sent back from the Cave eat once, then head back.
                if key in self._returning_for_food:
                    if hunger > 0:
                        self._assign(environment, component, "eat")
                        assigned.add(key)
                        if wheat > 0:
                            wheat -= 1
                    else:
                        self._assign(environment, component, "cave")
                        assigned.add(key)
                        self._returning_for_food.discard(key)
                # A newly spawned or otherwise fed Warrior can leave promptly.
                elif hunger >= 3:
                    self._assign(environment, component, "eat")
                    assigned.add(key)
                    if wheat > 0:
                        wheat -= 1
                else:
                    self._assign(environment, component, "cave")
                    assigned.add(key)
            else:
                farmers.append(component)

        # Feed Farmers before they reach six steps without a meal.
        for component in farmers:
            if component.steps_since_meal >= 5 and wheat > 0:
                self._assign(environment, component, "eat")
                assigned.add(id(component))
                wheat -= 1

        # Reserve food for Farmers who are close to their meal deadline.
        meal_reserve = sum(
            1 for component in farmers
            if id(component) not in assigned
            and component.steps_since_meal >= 4
        )
        available_wheat = max(0, wheat - meal_reserve)

        spawn_candidates = [
            component for component in farmers
            if id(component) not in assigned
        ]
        spawn_candidates.sort(
            key=lambda component: (component.steps_since_meal, -component.hp)
        )

        # Spawn Warriors first for damage, while also aiming to spawn Farmers.
        while len(spawn_candidates) >= 2:
            outstanding = [
                name for name in ("spawn warrior", "spawn farmer")
                if self._spawned[name] < 2
            ]
            if not outstanding:
                break

            spawn_group = min(
                outstanding,
                key=lambda name: (
                    self._spawned[name],
                    0 if name == "spawn warrior" else 1,
                ),
            )
            cost = 12 if spawn_group == "spawn warrior" else 10
            if available_wheat < cost:
                break

            pair = spawn_candidates[:2]
            spawn_candidates = spawn_candidates[2:]
            for component in pair:
                self._assign(environment, component, spawn_group)
                assigned.add(id(component))

            self._spawned[spawn_group] += 1
            available_wheat -= cost

        # Explicitly assign all remaining villagers.
        for component in components:
            if id(component) not in assigned:
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

        # Send at most one Warrior back per assignment, keeping other Warriors
        # attacking. A lone Warrior returns at hunger 5 to avoid starvation.
        eligible = [
            component for component in warriors
            if component.steps_since_meal >= 4
        ]
        eligible.sort(
            key=lambda component: (-component.steps_since_meal, -component.hp)
        )

        returning = None
        if len(warriors) == 1:
            if warriors[0].steps_since_meal >= 5:
                returning = warriors[0]
        elif eligible:
            returning = eligible[0]

        for component in warriors:
            if component is returning:
                self._assign(environment, component, "village")
                self._returning_for_food.add(id(component))
            else:
                self._assign(environment, component, "attack")