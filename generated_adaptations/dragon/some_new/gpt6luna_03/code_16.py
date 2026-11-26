from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def _assign(self, environment, component, group):
        environment.assign_group(component, group)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = max(0, getattr(environment.farm, "wheat", 0))
        dragon_hp = max(0, getattr(environment.dragon, "hp", 0))

        warriors = list(getattr(environment, "warriors", []))
        farmers = list(getattr(environment, "farmers", []))
        warrior_count = len(warriors)
        population = len(warriors) + len(farmers)
        available = list(components)

        if dragon_hp <= 0:
            for villager in available:
                self._assign(environment, villager, "farm")
            return

        # Feed the hungriest villagers present in the Village first.
        for villager in sorted(
            available,
            key=lambda c: getattr(c, "steps_since_meal", 0),
            reverse=True,
        ):
            if getattr(villager, "steps_since_meal", 0) >= 4 and wheat >= 1:
                self._assign(environment, villager, "eat")
                wheat -= 1
                available.remove(villager)

        # Keep a modest reserve for villagers who will need meals soon,
        # including cave villagers that are about to return to the Village.
        meals_due = sum(
            1
            for villager in warriors + farmers
            if getattr(villager, "steps_since_meal", 0) >= 3
        )
        meal_reserve = min(meals_due, max(1, population))

        # Prioritize spawning before reserving workers for the farm. This is
        # particularly important when there are no Warriors or few villagers.
        while (
            len(available) >= 2
            and wheat >= 12 + meal_reserve
            and warrior_count < max(6, population)
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

        # With no Warriors, retain a pair of villagers in the Village to
        # produce wheat until a spawn is affordable. Once Warriors exist,
        # retain a farmer only when reserves are low.
        farmers_here = [
            v for v in available if getattr(v, "role", "") == "Farmer"
        ]

        if warrior_count == 0:
            farm_count = min(2, len(available))
        elif wheat < 12 + meal_reserve:
            farm_count = min(1, len(available))
        else:
            farm_count = 0

        farm_workers = farmers_here[:farm_count]
        for worker in farm_workers:
            self._assign(environment, worker, "farm")
            available.remove(worker)

        # Any villagers not eating, spawning, or farming contribute damage.
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
                # Return before starvation; the next Village assignment can
                # provide a meal while the villager is still able to recover.
                self._assign(environment, villager, "village")
            else:
                self._assign(environment, villager, "attack")