The strategy keeps villagers fed, sends healthy villagers to attack, and rotates cave fighters back to the Village before they risk starvation. It maintains a small farming workforce when wheat is low, and spends surplus wheat to spawn Warriors (or Farmers when the population lacks them). Injured villagers are kept out of the Cave where possible. Every component is explicitly assigned on every call.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def _assign(self, environment, component, group_ids, name):
        if name not in group_ids:
            raise ValueError(f"Required group {name!r} is not available")
        environment.assign_group(component, name)

    def assign_in_village(self, components, environment, group_ids, step: int):
        villagers = list(components)
        wheat = max(0, getattr(environment.farm, "wheat", 0))

        # Feed the most urgent villagers first. Keep a local budget because
        # component attributes do not update after an assignment.
        hungry = sorted(
            (v for v in villagers if getattr(v, "steps_since_meal", 0) >= 4),
            key=lambda v: getattr(v, "steps_since_meal", 0),
            reverse=True,
        )
        assigned = set()
        for v in hungry:
            if wheat > 0:
                self._assign(environment, v, group_ids, "eat")
                wheat -= 1
                assigned.add(id(v))

        remaining = [v for v in villagers if id(v) not in assigned]

        # Use surplus wheat to spawn in pairs. Prefer Farmers if the population
        # has very few; otherwise recruit the more effective Dragon fighters.
        farmers = list(getattr(environment, "farmers", []))
        farmer_count = len(farmers)
        spawn_role = "spawn farmer" if farmer_count < 2 else "spawn warrior"
        spawn_cost = 10 if spawn_role == "spawn farmer" else 12
        reserve = 2
        eligible = sorted(
            (
                v for v in remaining
                if getattr(v, "hp", 0) > 1
                and getattr(v, "steps_since_meal", 0) < 4
            ),
            key=lambda v: getattr(v, "steps_since_meal", 0),
        )
        if wheat >= spawn_cost + reserve and len(eligible) >= 2:
            for v in eligible[:2]:
                self._assign(environment, v, group_ids, spawn_role)
                assigned.add(id(v))
            wheat -= spawn_cost

        remaining = [v for v in villagers if id(v) not in assigned]

        # When stores are low, keep at least one villager farming. Prefer a
        # Farmer, but use another healthy villager if none is available.
        farm_needed = wheat < 12
        farm_candidate = None
        if farm_needed:
            candidates = [v for v in remaining if getattr(v, "hp", 0) > 1]
            candidates.sort(
                key=lambda v: (
                    getattr(v, "role", "") != "Farmer",
                    getattr(v, "steps_since_meal", 0),
                )
            )
            if candidates:
                farm_candidate = candidates[0]

        for v in remaining:
            if id(v) in assigned:
                continue

            # Keep badly injured villagers out of the Cave.
            if getattr(v, "hp", 0) <= 1:
                self._assign(environment, v, group_ids, "farm")
            elif farm_candidate is v:
                self._assign(environment, v, group_ids, "farm")
            else:
                self._assign(environment, v, group_ids, "cave")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for v in components:
            hp = getattr(v, "hp", 0)
            meal_age = getattr(v, "steps_since_meal", 0)
            role = getattr(v, "role", "")

            # Return early enough to travel to the Village and eat before
            # reaching six consecutive steps without a meal.
            needs_food = meal_age >= 3

            # Retreat fragile villagers so they are less likely to be killed
            # by the Dragon's counterattacks.
            badly_injured = hp <= (1 if role == "Farmer" else 2)

            if needs_food or badly_injured:
                self._assign(environment, v, group_ids, "village")
            else:
                self._assign(environment, v, group_ids, "attack")
```