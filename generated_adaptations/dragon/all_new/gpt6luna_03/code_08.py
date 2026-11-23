from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._spawned_extra_farmer = False

    @staticmethod
    def _hunger(villager):
        return getattr(villager, "steps_since_meal", 0)

    def assign_in_village(self, components, environment, group_ids, step: int):
        villagers = list(components)
        assigned = set()
        wheat = max(0, environment.farm.wheat)
        population = len(environment.warriors) + len(environment.farmers)
        warrior_count = len(environment.warriors)
        farmer_count = len(environment.farmers)

        # Feed the hungriest villagers first. This prioritizes Cave returners,
        # who may have only one step left before starvation.
        for i in sorted(
            range(len(villagers)),
            key=lambda n: self._hunger(villagers[n]),
            reverse=True,
        ):
            if self._hunger(villagers[i]) >= 4 and wheat > 0:
                environment.assign_group(villagers[i], "eat")
                assigned.add(i)
                wheat -= 1

        remaining = [i for i in range(len(villagers)) if i not in assigned]
        dragon_hp = max(0, environment.dragon.hp)
        time_left = 30 - step

        # Spawn one villager per available pair when there is a meal reserve.
        # First ensure Warriors exist; later, use a surplus opportunity to
        # add a Farmer for sustained food production.
        if dragon_hp > 0 and time_left > 2 and len(remaining) >= 2:
            spawn_group = "spawn warrior"
            spawn_cost = 12

            if (
                warrior_count >= 2
                and farmer_count < 3
                and not self._spawned_extra_farmer
            ):
                spawn_group = "spawn farmer"
                spawn_cost = 10

            # Account for meals already assigned this turn.
            meal_reserve = max(1, population)
            if wheat >= spawn_cost + meal_reserve:
                candidates = sorted(
                    remaining,
                    key=lambda i: (
                        0 if villagers[i].role == "Farmer" else 1,
                        self._hunger(villagers[i]),
                    ),
                )
                for i in candidates[:2]:
                    environment.assign_group(villagers[i], spawn_group)
                    assigned.add(i)

                if spawn_group == "spawn farmer":
                    self._spawned_extra_farmer = True

        # Keep every Farmer in the Village: farming unless eating or spawning.
        for i, villager in enumerate(villagers):
            if i not in assigned and villager.role == "Farmer":
                environment.assign_group(villager, "farm")
                assigned.add(i)

        # Send available Warriors to attack. If wheat is exhausted, a Warrior
        # can farm rather than leave the Village with no food production.
        for i, villager in enumerate(villagers):
            if i in assigned:
                continue
            if environment.farm.wheat <= 0:
                environment.assign_group(villager, "farm")
            else:
                environment.assign_group(villager, "cave")
            assigned.add(i)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        dragon_hp = max(0, environment.dragon.hp)

        for villager in components:
            hunger = self._hunger(villager)
            hp = getattr(villager, "hp", 0)

            # Returning at four steps without food leaves time to travel to
            # the Village and eat before the six-step starvation point.
            if dragon_hp <= 0:
                environment.assign_group(villager, "cave")
            elif hunger >= 4 or hp <= 1:
                environment.assign_group(villager, "village")
            else:
                environment.assign_group(villager, "attack")