The missed Warrior spawns came from reserving wheat twice: the code deducted meals, then required the full population meal reserve again. This version checks the available wheat against the spawn cost plus the reserve directly, and uses an available pair—preferably two Farmers when a Farmer will remain to farm. It also avoids sending Warriors from the Village to the Cave when they are already too hungry to get useful attacks in.

```py
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

        if not villagers:
            return

        wheat = max(0, environment.farm.wheat)
        population = len(environment.warriors) + len(environment.farmers)
        warrior_count = len(environment.warriors)
        farmer_count = len(environment.farmers)
        dragon_hp = max(0, environment.dragon.hp)

        # Feed villagers approaching the starvation limit. Keep the wheat
        # amount separate from the spawn check below; the reserve is checked
        # against current stores, not subtracted twice.
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
        time_left = 30 - step

        if dragon_hp > 0 and time_left > 2 and len(remaining) >= 2:
            spawn_group = "spawn warrior"
            spawn_cost = 12

            # Establish a food-producing Farmer if none exist; otherwise
            # recruit Warriors to maximize damage.
            if farmer_count == 0:
                spawn_group = "spawn farmer"
                spawn_cost = 10
            elif (
                warrior_count >= 2
                and farmer_count < 3
                and not self._spawned_extra_farmer
            ):
                spawn_group = "spawn farmer"
                spawn_cost = 10

            # Match the reserve criterion directly: current wheat must cover
            # the recruit cost and one meal per current villager.
            if environment.farm.wheat >= spawn_cost + max(1, population):
                candidates = remaining[:]
                farmer_candidates = [
                    i for i in candidates if villagers[i].role == "Farmer"
                ]

                # When possible, use two Farmers for spawning but leave one
                # Farmer behind to keep producing food.
                if len(farmer_candidates) >= 3:
                    pair = farmer_candidates[:2]
                else:
                    # Prefer Farmers as spawners, then Warriors if needed.
                    candidates.sort(
                        key=lambda i: (
                            0 if villagers[i].role == "Farmer" else 1,
                            self._hunger(villagers[i]),
                        )
                    )
                    pair = candidates[:2]

                if len(pair) == 2:
                    for i in pair:
                        environment.assign_group(villagers[i], spawn_group)
                        assigned.add(i)

                    if spawn_group == "spawn farmer":
                        self._spawned_extra_farmer = True

        # Farmers not eating or spawning remain in the Village and farm.
        for i, villager in enumerate(villagers):
            if i in assigned:
                continue
            if villager.role == "Farmer":
                environment.assign_group(villager, "farm")
                assigned.add(i)

        # Send only recently fed Warriors to the Cave. Hungry Warriors eat
        # when food is available; if it is not, they farm until it is.
        for i, villager in enumerate(villagers):
            if i in assigned:
                continue

            if self._hunger(villager) >= 2:
                if environment.farm.wheat > 0:
                    environment.assign_group(villager, "eat")
                else:
                    environment.assign_group(villager, "farm")
            else:
                environment.assign_group(villager, "cave")
            assigned.add(i)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        dragon_hp = max(0, environment.dragon.hp)

        for villager in components:
            hunger = self._hunger(villager)
            hp = getattr(villager, "hp", 0)

            if dragon_hp <= 0:
                environment.assign_group(villager, "cave")
            elif hunger >= 4 or hp <= 1:
                environment.assign_group(villager, "village")
            else:
                environment.assign_group(villager, "attack")
```