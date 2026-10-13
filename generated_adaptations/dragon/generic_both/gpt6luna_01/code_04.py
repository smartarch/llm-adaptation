from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._spawned = {"spawn farmer": 0, "spawn warrior": 0}

    @staticmethod
    def _is_warrior(component):
        return str(component.role).lower() == "warrior"

    def _next_spawn_group(self, wheat):
        """Choose an affordable spawn type, favoring unmet targets."""
        choices = []

        for group, cost in (("spawn warrior", 12), ("spawn farmer", 10)):
            if wheat >= cost:
                choices.append((group, cost))

        if not choices:
            return None

        unmet = [
            group for group in ("spawn farmer", "spawn warrior")
            if self._spawned[group] < 2
        ]

        if unmet:
            # Work toward both minimum targets, breaking ties in favor of
            # Warriors for earlier Dragon damage.
            choices.sort(
                key=lambda item: (
                    0 if item[0] in unmet else 1,
                    self._spawned[item[0]] if item[0] in unmet else 0,
                    0 if item[0] == "spawn warrior" else 1,
                )
            )
        else:
            # After spawning at least two of each, prioritize more Warriors.
            choices.sort(key=lambda item: 0 if item[0] == "spawn warrior" else 1)

        return choices[0]

    def assign_in_village(self, components, environment, group_ids, step: int):
        farmers = []

        for component in components:
            if self._is_warrior(component):
                environment.assign_group(component, "cave")
            else:
                farmers.append(component)

        # Leave a Farmer working whenever there are enough villagers to do so
        # while still forming spawn pairs.
        max_pairs = len(farmers) // 2
        if len(farmers) >= 3:
            max_pairs = (len(farmers) - 1) // 2

        wheat = environment.farm.wheat
        used = 0

        while used < max_pairs:
            choice = self._next_spawn_group(wheat)
            if choice is None:
                break

            group, cost = choice
            pair = farmers[used * 2:used * 2 + 2]
            for component in pair:
                environment.assign_group(component, group)

            self._spawned[group] += 1
            wheat -= cost
            used += 1

        for component in farmers[used * 2:]:
            environment.assign_group(component, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for component in components:
            if self._is_warrior(component):
                environment.assign_group(component, "attack")
            else:
                environment.assign_group(component, "village")