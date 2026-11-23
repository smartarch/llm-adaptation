from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    @staticmethod
    def _hunger(villager):
        return int(getattr(villager, "steps_since_meal", 0))

    @staticmethod
    def _role(villager):
        return str(getattr(villager, "role", "")).lower()

    @staticmethod
    def _location(villager):
        return str(getattr(villager, "location", "")).lower()

    def assign_in_village(self, components, environment, group_ids, step: int):
        villagers = list(components)
        if not villagers:
            return

        wheat = max(0, int(getattr(environment.farm, "wheat", 0)))
        dragon_hp = max(0, int(getattr(environment.dragon, "hp", 0)))
        warriors = list(environment.warriors)
        farmers = list(environment.farmers)
        population = len(warriors) + len(farmers)

        assigned = set()

        # Feed villagers before sending them out or using them for other work.
        for villager in sorted(
            (v for v in villagers if self._hunger(v) >= 4),
            key=self._hunger,
            reverse=True,
        ):
            if wheat < 1:
                break
            environment.assign_group(villager, "eat")
            assigned.add(id(villager))
            wheat -= 1

        available = [v for v in villagers if id(v) not in assigned]

        # Reserve food for villagers who will need a meal soon, including
        # Cave villagers who are returning to the Village.
        soon_due = sum(
            1 for v in warriors + farmers if self._hunger(v) >= 3
        )
        meal_reserve = max(2, soon_due, (population + 5) // 6)

        # A sustainable workforce is about one farmer per 30 villagers.
        # When wheat is especially low, use a somewhat larger workforce to
        # rebuild the stock. Near the end, favor attacking over farming.
        farm_target = 0
        if dragon_hp > 20:
            sustainable_workers = max(1, (population + 29) // 30)
            if wheat < meal_reserve + 8:
                farm_target = max(
                    sustainable_workers,
                    (population + 19) // 20,
                )
            elif wheat < meal_reserve + 16:
                farm_target = sustainable_workers

        village_farmers = sum(
            1 for v in farmers if self._location(v) == "village"
        )
        workers_needed = max(0, farm_target - village_farmers)
        worker_candidates = sorted(
            available,
            key=lambda v: 0 if self._role(v) == "farmer" else 1,
        )
        for villager in worker_candidates[:workers_needed]:
            environment.assign_group(villager, "farm")
            assigned.add(id(villager))

        available = [v for v in villagers if id(v) not in assigned]

        # Spawn warriors only when food remains after the meal reserve.
        # Stop investing in new villagers late in the fight.
        if dragon_hp > 20 and step < 12:
            affordable_pairs = max(0, (wheat - meal_reserve) // 12)
            pairs = min(len(available) // 2, affordable_pairs)
            for villager in available[: 2 * pairs]:
                environment.assign_group(villager, "spawn warrior")
                assigned.add(id(villager))

        # Every remaining villager travels to the Cave.
        for villager in villagers:
            if id(villager) not in assigned:
                environment.assign_group(
                    villager, "cave" if dragon_hp > 0 else "farm"
                )

    def assign_in_cave(self, components, environment, group_ids, step: int):
        villagers = list(components)
        dragon_hp = max(0, int(getattr(environment.dragon, "hp", 0)))
        wheat = max(0, int(getattr(environment.farm, "wheat", 0)))
        population = len(environment.warriors) + len(environment.farmers)

        # If food is running low, bring back only enough farmers to help
        # maintain production; everyone else who is not due a meal attacks.
        desired_farmers = max(1, (population + 29) // 30)
        current_village_farmers = sum(
            1
            for v in environment.farmers
            if self._location(v) == "village"
        )
        need_farmers = max(0, desired_farmers - current_village_farmers)
        farmers_to_return = 0
        if dragon_hp > 20 and wheat < max(8, population // 2):
            farmers_to_return = need_farmers

        candidates = sorted(
            (
                v for v in villagers
                if self._role(v) == "farmer" and self._hunger(v) < 4
            ),
            key=lambda v: self._hunger(v),
        )
        returning_for_farm = {id(v) for v in candidates[:farmers_to_return]}

        for villager in villagers:
            if self._hunger(villager) >= 4:
                environment.assign_group(villager, "village")
            elif id(villager) in returning_for_farm:
                environment.assign_group(villager, "village")
            elif dragon_hp > 0:
                environment.assign_group(villager, "attack")
            else:
                environment.assign_group(villager, "village")