I’ll avoid spending wheat needed for imminent meals, keep a small farming workforce in the Village, and use surplus wheat to spawn warriors without leaving the farm empty. Warriors and other available villagers then attack, while cave villagers return early enough to travel home and eat. This balances sustained damage with food and replacement production, rather than relying on a fixed reserve or warrior target. **I can’t verify these changes against the simulator**, but they address the starvation and stalled-reinforcement patterns in the reports.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def _assign(self, environment, component, group):
        environment.assign_group(component, group)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = max(0, getattr(environment.farm, "wheat", 0))
        dragon_hp = max(0, getattr(environment.dragon, "hp", 0))

        all_warriors = list(getattr(environment, "warriors", []))
        all_farmers = list(getattr(environment, "farmers", []))
        population = len(all_warriors) + len(all_farmers)
        warrior_count = len(all_warriors)
        available = list(components)

        if dragon_hp <= 0:
            for villager in available:
                self._assign(environment, villager, "farm")
            return

        # Feed hungry villagers first. Keep track of the wheat spent here.
        for villager in sorted(
            available,
            key=lambda c: getattr(c, "steps_since_meal", 0),
            reverse=True,
        ):
            if getattr(villager, "steps_since_meal", 0) >= 4 and wheat >= 1:
                self._assign(environment, villager, "eat")
                wheat -= 1
                available.remove(villager)

        # Estimate meals that will soon be due, including for cave villagers.
        # This reserve prevents a spawn from using the last wheat needed to
        # feed villagers in the next step.
        meals_due = 0
        for villager in all_warriors + all_farmers:
            if getattr(villager, "steps_since_meal", 0) >= 3:
                meals_due += 1

        # Reserve at least a meal for every villager who is close to needing
        # food, but don't let an oversized reserve permanently block spawns.
        meal_reserve = min(meals_due, max(1, population))

        farmers_here = [
            v for v in available if getattr(v, "role", "") == "Farmer"
        ]
        farm_target = 1
        if wheat < max(4, population * 2) or warrior_count == 0:
            farm_target = 2

        # Reserve farmers for food production before selecting spawn pairs.
        farm_workers = farmers_here[:farm_target]
        for worker in farm_workers:
            available.remove(worker)

        # Spawn as soon as wheat can pay the cost without taking the meal
        # reserve. When no warriors exist, prioritize creating the first one.
        while len(available) >= 2 and wheat >= 12 + meal_reserve:
            if warrior_count >= max(6, population):
                break

            pair = sorted(
                available,
                key=lambda c: getattr(c, "role", "") != "Farmer",
            )[:2]

            for villager in pair:
                self._assign(environment, villager, "spawn warrior")
                available.remove(villager)

            wheat -= 12
            warrior_count += 1
            # The reserve grows with the force, but remains capped by the
            # population currently present.
            meal_reserve = min(meals_due, max(1, population + warrior_count))

        # Explicitly assign all retained farmers to the farm.
        for worker in farm_workers:
            self._assign(environment, worker, "farm")

        # Everyone else helps attack, including Farmers when they are not
        # required for feeding or spawning.
        for villager in available:
            self._assign(environment, villager, "cave")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        dragon_hp = max(0, getattr(environment.dragon, "hp", 0))

        for villager in components:
            hunger = getattr(villager, "steps_since_meal", 0)
            hp = getattr(villager, "hp", 0)

            if dragon_hp <= 0:
                self._assign(environment, villager, "cave")
            elif hunger >= 3 or hp <= 1:
                # A return trip uses a step, so leave before the villager is
                # at the starvation threshold.
                self._assign(environment, villager, "village")
            else:
                self._assign(environment, villager, "attack")
```