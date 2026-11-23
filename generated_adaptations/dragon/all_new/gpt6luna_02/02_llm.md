The strategy keeps cave fighters fed by sending them back to the Village before they reach the starvation threshold, then explicitly assigns them to eat when they arrive. In the Village, it prioritizes meals, farms when wheat is low, and uses surplus wheat and otherwise-idle Farmers to spawn Warriors. Healthy villagers are sent to attack whenever they are not needed for those tasks; spawning and farming are deprioritized when the Dragon is nearly dead.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def _assign(self, environment, component, group_ids, name):
        if name in group_ids:
            environment.assign_group(component, name)

    def assign_in_village(self, components, environment, group_ids, step: int):
        villagers = list(components)
        wheat = getattr(environment.farm, "wheat", 0)
        dragon_hp = getattr(environment.dragon, "hp", 0)

        # Feed villagers who are approaching starvation first. If wheat is
        # scarce, prioritize those who have gone longest without a meal.
        hungry = sorted(
            (v for v in villagers if getattr(v, "steps_since_meal", 0) >= 4),
            key=lambda v: getattr(v, "steps_since_meal", 0),
            reverse=True,
        )
        eaten = set()
        for villager in hungry:
            if wheat < 1:
                break
            self._assign(environment, villager, group_ids, "eat")
            wheat -= 1
            eaten.add(id(villager))

        remaining = [v for v in villagers if id(v) not in eaten]

        # Keep enough farming capacity to rebuild a low food supply.
        farmers = [v for v in remaining if getattr(v, "role", "") == "Farmer"]
        farm_count = 0
        if wheat < 5:
            farm_count = min(len(farmers), 2)
        elif wheat < 12:
            farm_count = min(len(farmers), 1)

        farm_workers = farmers[:farm_count]
        for villager in farm_workers:
            self._assign(environment, villager, group_ids, "farm")

        remaining = [v for v in remaining if id(v) not in {id(x) for x in farm_workers}]

        # When the Dragon is close to death, use villagers for combat rather
        # than spending a turn spawning. Otherwise, turn surplus Farmers into
        # Warriors when there is enough wheat to pay the cost.
        spawn_candidates = [
            v for v in remaining if getattr(v, "role", "") == "Farmer"
        ]
        if wheat >= 14 and dragon_hp > 30:
            pair_count = min(len(spawn_candidates) // 2, wheat // 12)
            for villager in spawn_candidates[: pair_count * 2]:
                self._assign(environment, villager, group_ids, "spawn warrior")
                wheat -= 6  # Reserve the cost across each two-person pair.

            spawned = {id(v) for v in spawn_candidates[: pair_count * 2]}
            remaining = [v for v in remaining if id(v) not in spawned]

        # Warriors are the strongest attackers. Send them first; send Farmers
        # too when food stocks permit or when there are no Warriors available.
        for villager in remaining:
            role = getattr(villager, "role", "")
            if role == "Warrior" or wheat >= 12 or dragon_hp <= 30:
                self._assign(environment, villager, group_ids, "cave")
            else:
                self._assign(environment, villager, group_ids, "farm")

        # Explicitly assign any component not handled above, including in
        # unusual cases where a group name was unavailable.
        assigned_ids = {
            id(v) for v in villagers
            if id(v) in eaten
            or id(v) in {id(x) for x in farm_workers}
            or id(v) in locals().get("spawned", set())
        }
        # The normal paths above assign every villager; this fallback keeps
        # the assignment explicit if the role or resource logic is unusual.
        for villager in villagers:
            if id(villager) not in assigned_ids and not any(
                getattr(villager, "role", "") == getattr(other, "role", None)
                and villager is other
                for other in ()
            ):
                # Remaining villagers were assigned to "cave" or "farm".
                # Reassigning is harmless and ensures a group is explicit.
                if getattr(villager, "role", "") == "Warrior" or wheat >= 12 or dragon_hp <= 30:
                    self._assign(environment, villager, group_ids, "cave")
                else:
                    self._assign(environment, villager, group_ids, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for villager in components:
            hunger = getattr(villager, "steps_since_meal", 0)
            hp = getattr(villager, "hp", 0)

            # Return early enough to reach the Village and eat before
            # starvation makes the villager unable to deal damage.
            if hunger >= 4 or hp <= 1:
                self._assign(environment, villager, group_ids, "village")
            else:
                self._assign(environment, villager, group_ids, "attack")
```