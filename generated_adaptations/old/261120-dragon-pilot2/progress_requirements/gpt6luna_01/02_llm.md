The strategy sends healthy, recently fed warriors to the Cave and keeps farmers in the Village. It rotates cave warriors back to eat before they become too hungry to fight, and prioritizes meals for villagers nearing starvation. When wheat and two available villagers allow it, it assigns a pair to spawn one farmer first, then two warriors; every component is explicitly assigned on every call.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._spawned_farmers = 0
        self._spawned_warriors = 0

    def _assign(self, environment, component, group_name, group_ids):
        # The group names are the valid group IDs supplied by the environment.
        group_id = group_name if group_name in group_ids else group_name
        environment.assign_group(component, group_id)

    def assign_in_village(self, components, environment, group_ids, step: int):
        villagers = list(components)
        wheat = max(0, environment.farm.wheat)

        # Farmers eat when close to the starvation threshold. Warriors eat
        # earlier so they can travel to the Cave and still fight while fed.
        meal_candidates = [
            c for c in villagers
            if (c.role == "Farmer" and c.steps_since_meal >= 5)
            or (c.role == "Warrior" and c.steps_since_meal >= 3)
        ]
        meal_candidates.sort(key=lambda c: c.steps_since_meal, reverse=True)

        # Assign meals only when there is wheat available, prioritizing the
        # villagers who have gone longest without eating.
        eaters = meal_candidates[:wheat]
        eaten_ids = {id(c) for c in eaters}
        for c in eaters:
            self._assign(environment, c, "eat", group_ids)

        remaining_wheat = max(0, wheat - len(eaters))
        spawn_workers = []

        # Spawn a farmer first to improve the food economy, then two warriors.
        if self._spawned_farmers < 1:
            spawn_role = "Farmer"
            spawn_cost = 10
        elif self._spawned_warriors < 2:
            spawn_role = "Warrior"
            spawn_cost = 12
        else:
            spawn_role = None
            spawn_cost = 0

        if spawn_role is not None and remaining_wheat >= spawn_cost:
            # Prefer farmers for spawning so existing warriors can keep
            # travelling to and attacking the Dragon.
            eligible = [
                c for c in villagers
                if id(c) not in eaten_ids and c.steps_since_meal < 5
            ]
            eligible.sort(
                key=lambda c: (
                    c.role != "Farmer",
                    c.steps_since_meal,
                )
            )
            spawn_workers = eligible[:2]

        spawned = (
            spawn_role is not None
            and len(spawn_workers) == 2
            and remaining_wheat >= spawn_cost
        )

        if spawned:
            group_name = "spawn farmer" if spawn_role == "Farmer" else "spawn warrior"
            for c in spawn_workers:
                self._assign(environment, c, group_name, group_ids)
            if spawn_role == "Farmer":
                self._spawned_farmers += 1
            else:
                self._spawned_warriors += 1

        spawn_worker_ids = {id(c) for c in spawn_workers} if spawned else set()

        # Explicitly assign every remaining villager. Farmers stay in the
        # Village to farm; warriors head to the Cave unless they need a meal.
        for c in villagers:
            if id(c) in eaten_ids or id(c) in spawn_worker_ids:
                continue
            if c.role == "Farmer":
                self._assign(environment, c, "farm", group_ids)
            elif c.steps_since_meal >= 3:
                # If wheat was unavailable for a meal above, keep the warrior
                # in the Village rather than send a hungry warrior to fight.
                self._assign(environment, c, "eat", group_ids)
            else:
                self._assign(environment, c, "cave", group_ids)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        dragon_alive = environment.dragon.hp > 0

        for c in components:
            if c.role == "Farmer":
                # Farmers should remain in, or return to, the Village.
                self._assign(environment, c, "village", group_ids)
            elif c.steps_since_meal >= 4:
                # Return early enough to travel home and eat before starving.
                self._assign(environment, c, "village", group_ids)
            elif dragon_alive and c.steps_since_meal < 6:
                self._assign(environment, c, "attack", group_ids)
            else:
                self._assign(environment, c, "cave", group_ids)
```