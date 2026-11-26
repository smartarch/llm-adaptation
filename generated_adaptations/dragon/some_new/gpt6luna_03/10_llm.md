The previous versions used arbitrary reserve and force-size limits that could delay spawning until the villagers needed to attack were already gone. This version spends available wheat on warrior spawns when the force is depleted, farms when wheat is short, and keeps cave fighters rotating back before starvation prevents them dealing damage. It assigns every villager on every call.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def _assign(self, environment, component, group):
        environment.assign_group(component, group)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = max(0, getattr(environment.farm, "wheat", 0))
        dragon_hp = max(0, getattr(environment.dragon, "hp", 0))

        warriors = list(getattr(environment, "warriors", []))
        farmers = list(getattr(environment, "farmers", []))
        warrior_count = len(warriors)
        population = warrior_count + len(farmers)
        available = list(components)

        if dragon_hp <= 0:
            for villager in available:
                self._assign(environment, villager, "farm")
            return

        # Feed villagers who are close to starvation before spending wheat on
        # spawning. The local wheat balance avoids over-allocating meals.
        for villager in sorted(
            available,
            key=lambda c: getattr(c, "steps_since_meal", 0),
            reverse=True,
        ):
            if getattr(villager, "steps_since_meal", 0) >= 4 and wheat >= 1:
                self._assign(environment, villager, "eat")
                wheat -= 1
                available.remove(villager)

        # Spawn replacements whenever the force is small. When no warriors
        # remain, do not delay spawning to preserve an arbitrary food reserve.
        target_warriors = 6
        while wheat >= 12 and warrior_count < target_warriors:
            local_farmers = [
                v for v in available
                if getattr(v, "role", "") == "Farmer"
            ]

            if len(local_farmers) >= 2:
                pair = local_farmers[:2]
            elif len(available) >= 2:
                pair = available[:2]
            else:
                break

            for villager in pair:
                self._assign(environment, villager, "spawn warrior")
                available.remove(villager)

            wheat -= 12
            warrior_count += 1

        # Keep food production alive when there is not enough wheat to spawn.
        # Prefer a Farmer; spare villagers should help attack instead.
        if wheat < 12 and available:
            farm_worker = next(
                (v for v in available if getattr(v, "role", "") == "Farmer"),
                None,
            )
            if farm_worker is not None:
                self._assign(environment, farm_worker, "farm")
                available.remove(farm_worker)

        for villager in available:
            self._assign(environment, villager, "cave")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        dragon_hp = max(0, getattr(environment.dragon, "hp", 0))

        for villager in components:
            hunger = getattr(villager, "steps_since_meal", 0)
            hp = getattr(villager, "hp", 0)

            if dragon_hp <= 0:
                self._assign(environment, villager, "cave")
            elif hunger >= 4 or hp <= 1:
                # Return early so there is time to travel home and eat.
                self._assign(environment, villager, "village")
            else:
                self._assign(environment, villager, "attack")
```