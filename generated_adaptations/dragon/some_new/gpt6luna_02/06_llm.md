The earlier policy could send all villagers into the Cave together, then pull them out together to eat, creating long gaps in attacks. This version staggers cave departures by villager, so most healthy fighters can keep attacking while a smaller group returns to eat. In the Village, it feeds hungry arrivals, builds enough wheat to recruit Warriors, and retains only a modest farming workforce when supplies are low.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def _assign(self, environment, component, group_ids, group):
        if group not in group_ids:
            raise ValueError(f"Required group {group!r} is not available")
        environment.assign_group(component, group)

    @staticmethod
    def _attr(component, name, default=0):
        return getattr(component, name, default)

    def assign_in_village(self, components, environment, group_ids, step: int):
        villagers = list(components)
        wheat = max(0, self._attr(environment.farm, "wheat", 0))
        warriors = list(getattr(environment, "warriors", []))
        farmers = list(getattr(environment, "farmers", []))
        warrior_count = len(warriors)
        population = warrior_count + len(farmers)
        assigned = set()

        # Feed villagers arriving from the Cave, and anyone approaching the
        # starvation limit, before allocating the remaining wheat.
        hungry = sorted(
            (v for v in villagers if self._attr(v, "steps_since_meal", 0) >= 4),
            key=lambda v: self._attr(v, "steps_since_meal", 0),
            reverse=True,
        )
        for v in hungry:
            if wheat > 0:
                self._assign(environment, v, group_ids, "eat")
                wheat -= 1
                assigned.add(id(v))

        available = [
            v for v in villagers
            if id(v) not in assigned
            and self._attr(v, "hp", 0) > 1
            and self._attr(v, "steps_since_meal", 0) < 5
        ]

        # Recruit Warriors as soon as two villagers and the cost are
        # available. Prioritize recruitment when there are none.
        recruit_target = 6
        if warrior_count < recruit_target and len(available) >= 2 and wheat >= 12:
            available.sort(
                key=lambda v: (
                    self._attr(v, "steps_since_meal", 0),
                    self._attr(v, "role", "") != "Farmer",
                )
            )
            for v in available[:2]:
                self._assign(environment, v, group_ids, "spawn warrior")
                assigned.add(id(v))
            wheat -= 12

        remaining = [v for v in villagers if id(v) not in assigned]

        # Keep a small number of villagers farming when stores are low.
        # Farmers are more productive, so select them first.
        if wheat < 10:
            farm_slots = 2
        elif wheat < 24:
            farm_slots = 1
        else:
            farm_slots = 0

        farm_candidates = [
            v for v in remaining
            if self._attr(v, "hp", 0) > 1
        ]
        farm_candidates.sort(
            key=lambda v: (
                self._attr(v, "role", "") != "Farmer",
                self._attr(v, "steps_since_meal", 0),
            )
        )
        farm_ids = {id(v) for v in farm_candidates[:farm_slots]}

        for v in remaining:
            if id(v) in assigned:
                continue
            if self._attr(v, "hp", 0) <= 1 or id(v) in farm_ids:
                self._assign(environment, v, group_ids, "farm")
            else:
                self._assign(environment, v, group_ids, "cave")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for v in components:
            age = self._attr(v, "steps_since_meal", 0)
            hp = self._attr(v, "hp", 0)

            # Stagger meal trips across villagers. Leaving by age four gives
            # time to travel to the Village and eat before starvation.
            # The stable per-object offset spreads departures over ages 2–4.
            return_age = 2 + (id(v) % 3)

            if age >= return_age or hp <= 1:
                self._assign(environment, v, group_ids, "village")
            else:
                self._assign(environment, v, group_ids, "attack")
```