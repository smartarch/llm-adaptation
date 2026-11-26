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

        # Eat first, prioritizing villagers closest to starvation.
        for villager in sorted(
            available,
            key=lambda c: getattr(c, "steps_since_meal", 0),
            reverse=True,
        ):
            if getattr(villager, "steps_since_meal", 0) >= 4 and wheat >= 1:
                self._assign(environment, villager, "eat")
                wheat -= 1
                available.remove(villager)

        # Build a fighting force. Do not reserve a farmer before looking for a
        # pair: with a small population that can otherwise block spawning.
        target_warriors = 6
        while wheat >= 12 and warrior_count < target_warriors:
            if population < 5 or warrior_count == 0:
                reserve = min(population, 3)
            else:
                reserve = min(population, 5)

            # A depleted force must be rebuilt even when reserves are tight.
            enough_reserve = wheat >= 12 + reserve
            if warrior_count > 0 and not enough_reserve:
                break

            farmers_here = [
                v for v in available if getattr(v, "role", "") == "Farmer"
            ]
            if len(farmers_here) >= 2:
                pair = farmers_here[:2]
            elif len(available) >= 2:
                pair = available[:2]
            else:
                break

            for villager in pair:
                self._assign(environment, villager, "spawn warrior")
                available.remove(villager)

            wheat -= 12
            warrior_count += 1

        # Maintain food production when possible. Prefer a farmer, but leave
        # the farm worker unassigned to combat only when reserves warrant it.
        if available:
            population_now = len(available) + len(
                [v for v in warriors if getattr(v, "location", "") == "Cave"]
            )
            food_floor = max(5, population_now)
            if wheat < food_floor:
                farm_worker = next(
                    (
                        v for v in available
                        if getattr(v, "role", "") == "Farmer"
                    ),
                    available[0],
                )
                self._assign(environment, farm_worker, "farm")
                available.remove(farm_worker)

        # Send remaining villagers to fight; farmers contribute damage too,
        # which is valuable when the Dragon is still alive.
        for villager in available:
            self._assign(environment, villager, "cave")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        dragon_hp = max(0, getattr(environment.dragon, "hp", 0))

        for villager in components:
            if dragon_hp <= 0:
                self._assign(environment, villager, "cave")
                continue

            hunger = getattr(villager, "steps_since_meal", 0)
            hp = getattr(villager, "hp", 0)

            # Leaving at four gives the villager a travel step and then a
            # Village assignment in which to eat before reaching starvation.
            if hunger >= 4 or hp <= 1:
                self._assign(environment, villager, "village")
            else:
                self._assign(environment, villager, "attack")