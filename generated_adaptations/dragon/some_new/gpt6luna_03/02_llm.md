The strategy prioritizes feeding villagers before they approach starvation, keeps a farmer working when wheat is low, and uses surplus wheat to spawn warriors. Healthy villagers are sent to attack; cave dwellers return to the Village when they need food or are too weak to fight. Every component is explicitly assigned on each call.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def _assign(self, environment, component, group):
        environment.assign_group(component, group)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = max(0, getattr(environment.farm, "wheat", 0))
        dragon_hp = max(0, getattr(environment.dragon, "hp", 0))
        population = len(getattr(environment, "warriors", [])) + len(
            getattr(environment, "farmers", [])
        )

        # Feed the hungriest villagers first, keeping a local estimate of wheat
        # so the same wheat is not allocated to multiple villagers.
        remaining = []
        for villager in sorted(
            components,
            key=lambda c: getattr(c, "steps_since_meal", 0),
            reverse=True,
        ):
            hungry = getattr(villager, "steps_since_meal", 0) >= 4
            if hungry and wheat >= 1:
                self._assign(environment, villager, "eat")
                wheat -= 1
            else:
                remaining.append(villager)

        farmers = [c for c in remaining if getattr(c, "role", "") == "Farmer"]
        others = [c for c in remaining if getattr(c, "role", "") != "Farmer"]

        # Keep food production going when reserves are low.
        food_target = max(8, 2 * population)
        farm_workers = []
        if wheat < food_target:
            if farmers:
                farm_workers.append(farmers.pop(0))
            elif others:
                farm_workers.append(others.pop(0))

        for villager in farm_workers:
            self._assign(environment, villager, "farm")

        # Spend only a genuine surplus on a warrior spawn, while leaving at
        # least one farmer available to keep producing wheat.
        spawn_threshold = max(20, 2 * population + 12)
        if (
            dragon_hp > 25
            and wheat >= spawn_threshold
            and len(farmers) >= 3
        ):
            for villager in farmers[:2]:
                self._assign(environment, villager, "spawn warrior")
            farmers = farmers[2:]
            wheat -= 12

        # Warriors are the most efficient attackers; farmers also attack when
        # available, particularly while the Dragon is still alive.
        for villager in others + farmers:
            self._assign(
                environment,
                villager,
                "cave" if dragon_hp > 0 else "farm",
            )

    def assign_in_cave(self, components, environment, group_ids, step: int):
        dragon_hp = max(0, getattr(environment.dragon, "hp", 0))

        for villager in components:
            if dragon_hp <= 0:
                self._assign(environment, villager, "cave")
                continue

            hunger = getattr(villager, "steps_since_meal", 0)
            hp = getattr(villager, "hp", 0)

            # Return villagers early enough to reach the Village and eat
            # before starvation, and avoid risking villagers too weak to fight.
            if hunger >= 4 or hp <= 1:
                self._assign(environment, villager, "village")
            else:
                self._assign(environment, villager, "attack")
```