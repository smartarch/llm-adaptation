The previous policy could get stuck because its food reserve and farming rules left too few villagers available to spawn warriors. This version feeds first, keeps only the minimum workforce needed for food production, and spends surplus wheat on warrior pairs early. Cave villagers return at hunger 4, and otherwise attack continuously; avoiding unnecessary trips is important because an unattended step lets the Dragon regenerate.

```py
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
        all_villagers = list(environment.warriors) + list(environment.farmers)
        population = max(1, len(all_villagers))

        assigned = set()

        # Feed villagers with the least time remaining before starvation.
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

        # Maintain a lean food-producing workforce. A farmer can produce
        # enough wheat to cover meals for roughly five villagers per step.
        desired_farmers = max(1, (population + 24) // 25)
        village_farmers = sum(
            1
            for v in environment.farmers
            if self._location(v) == "village"
        )
        workers_needed = max(0, desired_farmers - village_farmers)

        # When the stock is nearly empty, temporarily add a worker if possible.
        if wheat < max(3, population // 2):
            workers_needed = max(workers_needed, 1)

        worker_candidates = sorted(
            available,
            key=lambda v: 0 if self._role(v) == "farmer" else 1,
        )
        for villager in worker_candidates[:workers_needed]:
            environment.assign_group(villager, "farm")
            assigned.add(id(villager))

        available = [v for v in villagers if id(v) not in assigned]

        # Spend surplus wheat on warrior pairs early; avoid a fixed population
        # cap so a large starting stock can be converted into more damage.
        if dragon_hp > 0 and step < 18:
            due_meals = sum(
                1 for v in all_villagers if self._hunger(v) >= 3
            )
            reserve = min(3, due_meals)
            spawn_pairs = min(
                len(available) // 2,
                max(0, (wheat - reserve) // 12),
            )
            for villager in available[: 2 * spawn_pairs]:
                environment.assign_group(villager, "spawn warrior")
                assigned.add(id(villager))

        # Send everyone not eating, farming, or spawning to the Cave.
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
```