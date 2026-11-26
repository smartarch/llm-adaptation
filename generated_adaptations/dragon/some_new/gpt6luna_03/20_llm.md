The strategy should prioritize sustained attacks over building a large army: spawn only when the Warrior force is small, preserve wheat for imminent meals, and keep farming to the minimum needed to replenish food. Healthy villagers attack whenever they are not eating, spawning, or farming; cave fighters return before starvation or critical low health makes them ineffective. This is a targeted change, not a verified simulation result.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def _assign(self, environment, component, group):
        environment.assign_group(component, group)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = max(0, getattr(environment.farm, "wheat", 0))
        dragon_hp = max(0, getattr(environment.dragon, "hp", 0))

        warriors = list(getattr(environment, "warriors", []))
        farmers = list(getattr(environment, "farmers", []))
        population = len(warriors) + len(farmers)
        warrior_count = len(warriors)
        available = list(components)

        if dragon_hp <= 0:
            for villager in available:
                self._assign(environment, villager, "farm")
            return

        # Feed villagers who are closest to starvation first.
        for villager in sorted(
            available,
            key=lambda c: getattr(c, "steps_since_meal", 0),
            reverse=True,
        ):
            if getattr(villager, "steps_since_meal", 0) >= 4 and wheat >= 1:
                self._assign(environment, villager, "eat")
                wheat -= 1
                available.remove(villager)

        # Reserve food for villagers who will need meals imminently.
        meals_due = sum(
            1
            for villager in warriors + farmers
            if getattr(villager, "steps_since_meal", 0) >= 4
        )
        meal_reserve = min(meals_due, max(1, population))

        # Spawn replacements only while the fighting force is small. Avoid
        # spending wheat reserved for imminent meals.
        target_warriors = 3
        while (
            warrior_count < target_warriors
            and len(available) >= 2
            and wheat >= 12 + meal_reserve
        ):
            candidates = sorted(
                available,
                key=lambda c: getattr(c, "role", "") != "Farmer",
            )
            pair = candidates[:2]

            for villager in pair:
                self._assign(environment, villager, "spawn warrior")
                available.remove(villager)

            wheat -= 12
            warrior_count += 1

        # If there are no warriors and wheat is not yet sufficient to spawn,
        # use two villagers to build the supply. Otherwise farm with at most
        # one villager when reserves are low.
        farmers_here = [
            villager
            for villager in available
            if getattr(villager, "role", "") == "Farmer"
        ]

        if warrior_count == 0 and wheat < 12 + meal_reserve:
            farm_workers = farmers_here[:2]
        elif wheat < max(5, population):
            farm_workers = farmers_here[:1]
        else:
            farm_workers = []

        for worker in farm_workers:
            self._assign(environment, worker, "farm")
            available.remove(worker)

        # All remaining villagers contribute damage rather than being held
        # back for an oversized reserve or force target.
        for villager in available:
            self._assign(environment, villager, "cave")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        dragon_hp = max(0, getattr(environment.dragon, "hp", 0))

        for villager in components:
            hunger = getattr(villager, "steps_since_meal", 0)
            hp = getattr(villager, "hp", 0)

            if dragon_hp <= 0:
                self._assign(environment, villager, "cave")
            elif hunger >= 4 or hp <= 2:
                self._assign(environment, villager, "village")
            else:
                self._assign(environment, villager, "attack")
```