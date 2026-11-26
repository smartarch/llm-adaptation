from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def _assign(self, environment, component, group):
        environment.assign_group(component, group)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = max(0, getattr(environment.farm, "wheat", 0))
        dragon_hp = max(0, getattr(environment.dragon, "hp", 0))

        all_villagers = (
            list(getattr(environment, "warriors", []))
            + list(getattr(environment, "farmers", []))
        )
        population = len(all_villagers)
        warrior_count = len(getattr(environment, "warriors", []))

        unassigned = list(components)

        # Feed those closest to starvation first. Track wheat locally because
        # the component attributes do not change after an assignment.
        for villager in sorted(
            unassigned,
            key=lambda c: getattr(c, "steps_since_meal", 0),
            reverse=True,
        )[:]:
            if getattr(villager, "steps_since_meal", 0) >= 4 and wheat >= 1:
                self._assign(environment, villager, "eat")
                wheat -= 1
                unassigned.remove(villager)

        # Spawn warriors early, especially when there are none. Keep enough
        # wheat aside for a small meal reserve before spending the 12 wheat.
        spawned = 0
        while dragon_hp > 0 and warrior_count + spawned < 3:
            farmers = [c for c in unassigned if getattr(c, "role", "") == "Farmer"]
            candidates = farmers if len(farmers) >= 2 else unassigned
            if len(candidates) < 2:
                break

            meal_reserve = min(population, 4)
            if wheat < 12 + meal_reserve:
                break

            pair = candidates[:2]
            for villager in pair:
                self._assign(environment, villager, "spawn warrior")
                unassigned.remove(villager)

            wheat -= 12
            spawned += 1

        # Keep at least one villager farming when reserves are low. Prefer a
        # Farmer, but use another villager if necessary.
        food_target = max(8, 2 * population)
        if wheat < food_target and unassigned:
            farmer = next(
                (c for c in unassigned if getattr(c, "role", "") == "Farmer"),
                unassigned[0],
            )
            self._assign(environment, farmer, "farm")
            unassigned.remove(farmer)

        # Send all remaining healthy villagers to help damage the Dragon.
        for villager in unassigned:
            self._assign(
                environment,
                villager,
                "cave" if dragon_hp > 0 else "farm",
            )

    def assign_in_cave(self, components, environment, group_ids, step: int):
        dragon_hp = max(0, getattr(environment.dragon, "hp", 0))

        for villager in components:
            hunger = getattr(villager, "steps_since_meal", 0)
            hp = getattr(villager, "hp", 0)

            if dragon_hp <= 0:
                self._assign(environment, villager, "cave")
            elif hunger >= 4 or hp <= 1:
                # Leave with enough time to travel to the Village and eat.
                self._assign(environment, villager, "village")
            else:
                self._assign(environment, villager, "attack")