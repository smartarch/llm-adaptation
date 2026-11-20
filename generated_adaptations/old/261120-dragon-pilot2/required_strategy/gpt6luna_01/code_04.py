from math import ceil

from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._village_count = 0
        self._cave_count = 0
        self._has_spawned_farmer = False

    def assign_in_village(self, components, environment, group_ids, step: int):
        villagers = list(components)
        self._village_count = len(villagers)

        wheat = max(0, int(environment.farm.wheat))
        population_estimate = self._village_count + self._cave_count
        meal_reserve = max(3, ceil(population_estimate / 3) + 1)

        # Feed villagers nearing starvation before assigning other tasks.
        needing_food = sorted(
            (v for v in villagers if v.steps_since_meal >= 4),
            key=lambda v: (-v.steps_since_meal, v.hp),
        )
        eaters = set()
        for villager in needing_food[:wheat]:
            environment.assign_group(villager, "eat")
            eaters.add(villager)

        available = [v for v in villagers if v not in eaters]
        farmers = [v for v in available if v.role == "Farmer"]

        # Ensure at least one Farmer is spawned before considering Warriors.
        spawn_group = set()
        if (
            not self._has_spawned_farmer
            and wheat >= 10
            and len(available) >= 2
        ):
            candidates = sorted(
                available,
                key=lambda v: (v.role != "Farmer", -v.hp),
            )
            spawn_group.update(candidates[:2])
            for villager in spawn_group:
                environment.assign_group(villager, "spawn farmer")
            self._has_spawned_farmer = True

        # Once a Farmer has been spawned, use surplus wheat to add Warriors.
        elif (
            self._has_spawned_farmer
            and environment.dragon.hp > 0
            and len(farmers) >= 2
            and wheat >= 12 + meal_reserve
        ):
            candidates = sorted(farmers, key=lambda v: -v.hp)
            spawn_group.update(candidates[:2])
            for villager in spawn_group:
                environment.assign_group(villager, "spawn warrior")

        for villager in villagers:
            if villager in eaters or villager in spawn_group:
                continue
            if villager.role == "Farmer":
                environment.assign_group(villager, "farm")
            else:
                environment.assign_group(villager, "cave")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        villagers = list(components)
        self._cave_count = len(villagers)

        for villager in villagers:
            if villager.role != "Warrior":
                environment.assign_group(villager, "village")
            elif villager.steps_since_meal >= 4 or villager.hp <= 1:
                environment.assign_group(villager, "village")
            else:
                environment.assign_group(villager, "attack")