The previous version could leave a hungry fighter in the Cave too long, or send a fighter back before they had contributed enough attacks. This version rotates Cave villagers back at hunger 4 so they can travel and eat before starvation, while otherwise keeping them attacking. In the Village it feeds hungry villagers, keeps a Farmer farming when possible, and spawns a Warrior when there is enough wheat and a pair of villagers available.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def assign_in_village(self, components, environment, group_ids, step: int):
        villagers = list(components)
        if not villagers:
            return

        assigned = set()
        wheat = max(0, environment.farm.wheat)
        population = len(environment.warriors) + len(environment.farmers)
        warrior_count = len(environment.warriors)
        farmer_count = len(environment.farmers)
        dragon_hp = max(0, environment.dragon.hp)

        def hunger(v):
            return getattr(v, "steps_since_meal", 0)

        # Eat while there is still a margin before the starvation threshold.
        for i in sorted(
            range(len(villagers)),
            key=lambda j: hunger(villagers[j]),
            reverse=True,
        ):
            if hunger(villagers[i]) >= 4 and wheat > 0:
                environment.assign_group(villagers[i], "eat")
                assigned.add(i)
                wheat -= 1

        # Try to recruit while there is time for the recruit to help and
        # enough wheat remains to protect the food reserve.
        remaining = [i for i in range(len(villagers)) if i not in assigned]
        time_left = 30 - step
        cost = 12
        spawn_group = "spawn warrior"

        # If no Warriors exist, prioritize the first Warrior recruit. If the
        # group has no Farmers at all, recruit a Farmer instead.
        if farmer_count == 0 and warrior_count >= 1:
            spawn_group = "spawn farmer"
            cost = 10

        if dragon_hp > 0 and time_left > 1 and len(remaining) >= 2:
            meal_reserve = max(1, population)
            if environment.farm.wheat >= cost + meal_reserve:
                # Preserve a working Farmer when possible, except when there
                # are no Warriors and the pair is needed to create one.
                candidates = remaining[:]
                if warrior_count > 0:
                    farmers_here = [
                        i for i in candidates if villagers[i].role == "Farmer"
                    ]
                    if len(farmers_here) >= 1:
                        # Prefer a pair that leaves a Farmer available to farm.
                        preserve = farmers_here[0]
                        candidates = [i for i in candidates if i != preserve]

                if len(candidates) >= 2:
                    candidates.sort(
                        key=lambda i: (
                            0 if villagers[i].role == "Farmer" else 1,
                            hunger(villagers[i]),
                        )
                    )
                    for i in candidates[:2]:
                        environment.assign_group(villagers[i], spawn_group)
                        assigned.add(i)

        # Leave at least one available Farmer working in the Village.
        for i, villager in enumerate(villagers):
            if i not in assigned and villager.role == "Farmer":
                environment.assign_group(villager, "farm")
                assigned.add(i)
                break

        # Any other Farmers can help replenish food. Unassigned Warriors
        # should head to the Cave rather than remain idle.
        for i, villager in enumerate(villagers):
            if i in assigned:
                continue
            if villager.role == "Farmer" and max(0, environment.farm.wheat) < population:
                environment.assign_group(villager, "farm")
            else:
                environment.assign_group(villager, "cave")
            assigned.add(i)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        dragon_hp = max(0, environment.dragon.hp)

        for villager in components:
            hunger = getattr(villager, "steps_since_meal", 0)
            hp = getattr(villager, "hp", 0)

            # Leaving at four steps gives the villager time to travel to the
            # Village and eat before reaching six consecutive steps without
            # a meal. Retreat only from imminent death otherwise, to avoid
            # sacrificing too much attack time.
            if hunger >= 4 or (hp <= 1 and dragon_hp > 0):
                environment.assign_group(villager, "village")
            else:
                environment.assign_group(villager, "attack")
```