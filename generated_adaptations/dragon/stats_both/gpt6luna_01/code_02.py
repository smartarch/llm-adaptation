from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._spawned_farmers = 0
        self._spawned_warriors = 0

    @staticmethod
    def _role(component):
        return str(component.role).lower()

    @staticmethod
    def _hunger(component):
        return int(component.steps_since_meal)

    def assign_in_village(self, components, environment, group_ids, step: int):
        components = list(components)
        wheat = max(0, int(environment.farm.wheat))

        # Eat before the starvation deadline. Warriors also eat at age 3 or
        # more before being sent back to the Cave.
        due = []
        for component in components:
            age = self._hunger(component)
            threshold = 3 if self._role(component) == "warrior" else 5
            if age >= threshold:
                due.append(component)

        due.sort(key=lambda c: (self._hunger(c), -int(c.hp)), reverse=True)
        eaters = due[:wheat]
        eat_ids = {id(c) for c in eaters}
        unmet_due = len(eaters) < len(due)

        actions = {}
        for component in components:
            if id(component) in eat_ids:
                actions[id(component)] = "eat"
            elif self._role(component) == "warrior" and self._hunger(component) < 3:
                actions[id(component)] = "cave"
            else:
                # Farmers remain in the Village; warriors without food can
                # farm temporarily while they wait to eat.
                actions[id(component)] = "farm"

        wheat_after_meals = max(0, wheat - len(eaters))
        candidates = [c for c in components if id(c) not in eat_ids]
        # Prefer using farmers for spawning, so warriors can reach the Cave.
        candidates.sort(
            key=lambda c: (
                self._role(c) != "farmer",
                self._hunger(c),
            )
        )

        # Spend on spawning only after meals are covered, and retain a small
        # reserve for upcoming meals and returning warriors.
        reserve = 2
        if not unmet_due:
            if self._spawned_farmers < 1:
                if len(candidates) >= 2 and wheat_after_meals >= 10 + reserve:
                    for component in candidates[:2]:
                        actions[id(component)] = "spawn farmer"
                    self._spawned_farmers += 1
            else:
                needed = max(0, 2 - self._spawned_warriors)
                affordable_pairs = max(0, (wheat_after_meals - reserve) // 12)
                pair_count = min(needed, affordable_pairs, len(candidates) // 2)
                for component in candidates[: 2 * pair_count]:
                    actions[id(component)] = "spawn warrior"
                self._spawned_warriors += pair_count

        for component in components:
            environment.assign_group(component, actions[id(component)])

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for component in components:
            if self._role(component) == "farmer":
                # Farmers stay in the Village, where they can work or eat.
                action = "village"
            elif self._hunger(component) >= 4:
                # Return in time to travel home and eat before starvation.
                action = "village"
            else:
                action = "attack"

            environment.assign_group(component, action)