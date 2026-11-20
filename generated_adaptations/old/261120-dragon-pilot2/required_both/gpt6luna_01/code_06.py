from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._warrior_spawn_orders = 0
        self._farmer_spawn_orders = 0

    @staticmethod
    def _role(component):
        return getattr(component, "role", "")

    @staticmethod
    def _age(component):
        return max(0, getattr(component, "steps_since_meal", 0))

    def assign_in_village(self, components, environment, group_ids, step: int):
        decisions = {}
        wheat = max(0, getattr(environment.farm, "wheat", 0))

        # Eat before starvation becomes a risk. Warriors are fed earlier so
        # they can travel to the Cave without arriving too hungry to fight.
        hungry = sorted(
            (
                c for c in components
                if (self._role(c) == "Warrior" and self._age(c) >= 3)
                or (self._role(c) != "Warrior" and self._age(c) >= 5)
            ),
            key=self._age,
            reverse=True,
        )
        for c in hungry:
            if wheat <= 0:
                break
            decisions[c] = "eat"
            wheat -= 1

        # Preserve some wheat for meals, especially when villagers are already
        # approaching their next meal.
        reserve = 2 + sum(1 for c in components if self._age(c) >= 3)
        reserve = min(reserve, 8)

        candidates = [
            c for c in components
            if c not in decisions and self._age(c) < 5
        ]
        # Use Farmers for spawning first, keeping Warriors available to attack.
        candidates.sort(key=lambda c: self._role(c) != "Farmer")

        def spawn(group, cost, number_needed):
            nonlocal wheat
            spawned = 0
            while (
                number_needed > 0
                and len(candidates) >= 2
                and wheat >= cost + reserve
            ):
                first = candidates.pop(0)
                second = candidates.pop(0)
                decisions[first] = group
                decisions[second] = group
                wheat -= cost
                number_needed -= 1
                spawned += 1
            return spawned

        # Recruit beyond the minimum so the attack can overcome Dragon damage
        # and regeneration within the step limit.
        self._warrior_spawn_orders += spawn(
            "spawn warrior", 12, max(0, 6 - self._warrior_spawn_orders)
        )

        # Ensure at least one additional Farmer is recruited as well.
        self._farmer_spawn_orders += spawn(
            "spawn farmer", 10, max(0, 1 - self._farmer_spawn_orders)
        )

        for c in components:
            if c in decisions:
                continue
            if self._role(c) == "Farmer":
                decisions[c] = "farm"
            elif self._age(c) >= 3:
                decisions[c] = "eat"
            else:
                decisions[c] = "cave"

        for component in components:
            environment.assign_group(component, decisions[component])

    def assign_in_cave(self, components, environment, group_ids, step: int):
        warriors = [
            c for c in components
            if self._role(c) == "Warrior"
        ]

        # Return Warriors at age 5, and stagger age-4 returns where possible.
        # This helps avoid sending the whole attacking force home together.
        age_four = sorted(
            (c for c in warriors if self._age(c) == 4),
            key=self._age,
            reverse=True,
        )
        staggered_return = age_four[:1]

        for component in components:
            if self._role(component) != "Warrior":
                group = "village"
            elif self._age(component) >= 5 or component in staggered_return:
                group = "village"
            else:
                group = "attack"

            environment.assign_group(component, group)