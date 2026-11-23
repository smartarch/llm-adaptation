from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    @staticmethod
    def _hunger(villager):
        return int(getattr(villager, "steps_since_meal", 0))

    @staticmethod
    def _role(villager):
        return str(getattr(villager, "role", "")).lower()

    def assign_in_village(self, components, environment, group_ids, step: int):
        villagers = list(components)
        if not villagers:
            return

        wheat = max(0, int(getattr(environment.farm, "wheat", 0)))
        dragon_hp = max(0, int(getattr(environment.dragon, "hp", 0)))
        population = len(environment.warriors) + len(environment.farmers)

        assigned = set()

        # Feed villagers whose hunger is high enough that they should not
        # start another trip or work cycle without eating.
        hungry = sorted(
            (v for v in villagers if self._hunger(v) >= 4),
            key=self._hunger,
            reverse=True,
        )
        for villager in hungry:
            if wheat <= 0:
                break
            environment.assign_group(villager, "eat")
            assigned.add(id(villager))
            wheat -= 1

        available = [v for v in villagers if id(v) not in assigned]

        # Keep a sustainable farming workforce explicitly assigned each step.
        # Five wheat per farmer per step supports roughly 30 villagers'
        # average meal needs.
        farm_target = max(1, (population + 29) // 30) if dragon_hp > 0 else 0
        workers = sorted(
            available,
            key=lambda v: (self._role(v) != "farmer", self._hunger(v)),
        )[:farm_target]

        for villager in workers:
            environment.assign_group(villager, "farm")
            assigned.add(id(villager))

        available = [v for v in villagers if id(v) not in assigned]

        # Keep a modest buffer for imminent meals, and spend only wheat above
        # that buffer on spawning. Spawn early enough for new warriors to fight.
        imminent_meals = sum(
            1
            for v in list(environment.warriors) + list(environment.farmers)
            if self._hunger(v) >= 3
        )
        meal_reserve = max(2, min(population, imminent_meals))
        if dragon_hp > 0 and step < 20:
            pairs = min(
                len(available) // 2,
                max(0, (wheat - meal_reserve) // 12),
            )
            for villager in available[: 2 * pairs]:
                environment.assign_group(villager, "spawn warrior")
                assigned.add(id(villager))

        # All other villagers head to the Cave.
        for villager in villagers:
            if id(villager) not in assigned:
                environment.assign_group(
                    villager, "cave" if dragon_hp > 0 else "farm"
                )

    def assign_in_cave(self, components, environment, group_ids, step: int):
        dragon_hp = max(0, int(getattr(environment.dragon, "hp", 0)))

        for villager in components:
            if self._hunger(villager) >= 4 or dragon_hp <= 0:
                environment.assign_group(villager, "village")
            else:
                environment.assign_group(villager, "attack")