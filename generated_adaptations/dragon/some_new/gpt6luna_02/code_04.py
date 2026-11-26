from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def _assign(self, environment, component, group_ids, group):
        if group not in group_ids:
            raise ValueError(f"Required group {group!r} is not available")
        environment.assign_group(component, group)

    @staticmethod
    def _value(component, attribute, default=0):
        return getattr(component, attribute, default)

    def assign_in_village(self, components, environment, group_ids, step: int):
        villagers = list(components)
        wheat = max(0, self._value(environment.farm, "wheat", 0))
        dragon_hp = max(0, self._value(environment.dragon, "hp", 100))

        all_warriors = list(getattr(environment, "warriors", []))
        all_farmers = list(getattr(environment, "farmers", []))
        warrior_count = len(all_warriors)
        population = warrior_count + len(all_farmers)

        assigned_ids = set()

        # Feed first so villagers do not become too weak to fight.
        # Keep the local wheat budget conservative because attributes do not
        # update after group assignments.
        urgent = sorted(
            (v for v in villagers if self._value(v, "steps_since_meal", 0) >= 4),
            key=lambda v: self._value(v, "steps_since_meal", 0),
            reverse=True,
        )
        for v in urgent:
            if wheat > 0:
                self._assign(environment, v, group_ids, "eat")
                wheat -= 1
                assigned_ids.add(id(v))

        remaining = [v for v in villagers if id(v) not in assigned_ids]

        # During the final push, prioritize getting every available villager
        # to the Cave rather than spending a turn on recruitment or farming.
        final_push = dragon_hp <= 18
        eligible = [
            v for v in remaining
            if self._value(v, "hp", 0) > 1
            and self._value(v, "steps_since_meal", 0) < 5
        ]

        # Recruit Warriors early, especially if no Warriors remain. Require
        # enough wheat to pay the spawn cost and retain a modest food reserve.
        if not final_push and len(eligible) >= 2 and warrior_count < 3:
            reserve = min(population, 5) if warrior_count > 0 else 0
            if wheat >= 12 + reserve:
                # Prefer villagers who are not urgently hungry.
                eligible.sort(
                    key=lambda v: (
                        self._value(v, "steps_since_meal", 0),
                        self._value(v, "role", "") != "Farmer",
                    )
                )
                for v in eligible[:2]:
                    self._assign(environment, v, group_ids, "spawn warrior")
                    assigned_ids.add(id(v))
                wheat -= 12

        remaining = [v for v in villagers if id(v) not in assigned_ids]

        # When the population is small and stores permit it, grow the farming
        # workforce. Do this only when Warrior recruitment is not the priority.
        farmer_count = len(all_farmers)
        available = [
            v for v in remaining
            if self._value(v, "hp", 0) > 1
            and self._value(v, "steps_since_meal", 0) < 5
        ]
        if (
            not final_push
            and warrior_count >= 2
            and population < 5
            and farmer_count < 2
            and wheat >= 10 + population
            and len(available) >= 2
        ):
            available.sort(
                key=lambda v: (
                    self._value(v, "role", "") != "Farmer",
                    self._value(v, "steps_since_meal", 0),
                )
            )
            for v in available[:2]:
                self._assign(environment, v, group_ids, "spawn farmer")
                assigned_ids.add(id(v))

        remaining = [v for v in villagers if id(v) not in assigned_ids]

        # Keep workers in the Village when supplies are low. Farmers are
        # preferred because they produce more wheat.
        if not final_push:
            if wheat < 10:
                farm_slots = 2
            elif wheat < 25:
                farm_slots = 1
            else:
                farm_slots = 0

            candidates = [v for v in remaining if self._value(v, "hp", 0) > 1]
            candidates.sort(
                key=lambda v: (
                    self._value(v, "role", "") != "Farmer",
                    self._value(v, "steps_since_meal", 0),
                )
            )
            farm_ids = {id(v) for v in candidates[:farm_slots]}
        else:
            farm_ids = set()

        for v in remaining:
            if id(v) in assigned_ids:
                continue

            if self._value(v, "hp", 0) <= 1:
                self._assign(environment, v, group_ids, "farm")
            elif id(v) in farm_ids:
                self._assign(environment, v, group_ids, "farm")
            else:
                self._assign(environment, v, group_ids, "cave")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        dragon_hp = max(0, self._value(environment.dragon, "hp", 100))
        final_push = dragon_hp <= 18

        for v in components:
            hp = self._value(v, "hp", 0)
            meal_age = self._value(v, "steps_since_meal", 0)

            # Return in time to reach the Village and eat before starvation.
            needs_food = meal_age >= 3

            # Retreat only critically injured villagers; otherwise keep
            # applying damage before the Dragon can recover.
            critically_injured = hp <= 1

            if not final_push and (needs_food or critically_injured):
                self._assign(environment, v, group_ids, "village")
            else:
                self._assign(environment, v, group_ids, "attack")