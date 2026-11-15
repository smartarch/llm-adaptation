The strategy sends healthy, fed Warriors to attack immediately and staggers their returns for meals, reducing the chance that the Dragon gets a long regeneration window. Farmers eat before they risk starvation; otherwise they farm, with two Farmers assigned together to spawn the first two Warriors and then two Farmers when wheat and workers allow. Each component is explicitly assigned on every call.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._spawned_warriors = 0
        self._spawned_farmers = 0

    @staticmethod
    def _assign(environment, component, group_name, group_ids):
        if group_name not in group_ids:
            raise ValueError(f"Required group {group_name!r} is not available")
        environment.assign_group(component, group_name)

    def assign_in_village(self, components, environment, group_ids, step: int):
        farmers_to_work = []
        meals = 0

        # Feed villagers before assigning workers to spawning or farming.
        for component in components:
            if component.role == "Farmer":
                if component.steps_since_meal >= 5:
                    self._assign(environment, component, "eat", group_ids)
                    meals += 1
                else:
                    farmers_to_work.append(component)
            else:  # Warrior
                if component.steps_since_meal >= 4:
                    self._assign(environment, component, "eat", group_ids)
                    meals += 1
                else:
                    self._assign(environment, component, "cave", group_ids)

        # Spawn in pairs, first prioritizing Warriors. Leave a small wheat
        # reserve beyond the meals assigned this step.
        wheat_budget = max(0, environment.farm.wheat - meals - 2)
        spawn_plans = []
        if self._spawned_warriors < 2:
            spawn_plans.append(("spawn warrior", 12, "warrior"))
        if self._spawned_farmers < 2:
            spawn_plans.append(("spawn farmer", 10, "farmer"))

        available = list(farmers_to_work)
        for group_name, cost, role in spawn_plans:
            if len(available) < 2 or wheat_budget < cost:
                continue

            for component in available[:2]:
                self._assign(environment, component, group_name, group_ids)
            del available[:2]
            wheat_budget -= cost

            if role == "warrior":
                self._spawned_warriors += 1
            else:
                self._spawned_farmers += 1

        for component in available:
            self._assign(environment, component, "farm", group_ids)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for index, component in enumerate(components):
            if component.role != "Warrior":
                self._assign(environment, component, "village", group_ids)
                continue

            # Split meal departures across consecutive hunger levels where
            # possible; at four steps without a meal, everyone returns.
            should_return = (
                component.steps_since_meal >= 4
                or (
                    component.steps_since_meal >= 3
                    and index % 2 == 0
                )
            )

            if should_return:
                self._assign(environment, component, "village", group_ids)
            else:
                self._assign(environment, component, "attack", group_ids)
```