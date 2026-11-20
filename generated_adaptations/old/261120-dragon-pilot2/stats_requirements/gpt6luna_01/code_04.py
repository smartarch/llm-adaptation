from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._warrior_spawned = 0
        self._farmer_spawned = False

    @staticmethod
    def _role(component):
        return str(component.role).lower()

    @staticmethod
    def _valid_group(name, group_ids):
        for group_id in group_ids:
            if str(group_id) == name:
                return group_id
        return name

    def _assign(self, environment, component, name, group_ids):
        environment.assign_group(
            component, self._valid_group(name, group_ids)
        )

    def assign_in_village(self, components, environment, group_ids, step: int):
        components = list(components)
        wheat = max(0, int(environment.farm.wheat))
        assigned = set()

        # Feed villagers before they become critically hungry.
        meal_candidates = sorted(
            (
                c for c in components
                if c.steps_since_meal >= 5
            ),
            key=lambda c: c.steps_since_meal,
            reverse=True,
        )
        for component in meal_candidates:
            if wheat <= 0:
                break
            self._assign(environment, component, "eat", group_ids)
            assigned.add(id(component))
            wheat -= 1

        available = [c for c in components if id(c) not in assigned]
        farmers = [c for c in available if self._role(c) == "farmer"]

        # Spawn warriors repeatedly, up to a useful group size. Use farmers
        # for spawning where possible, but leave at least one farmer farming.
        spawn_pair = None
        if self._warrior_spawned < 6 and wheat >= 12:
            if len(farmers) >= 3:
                spawn_pair = farmers[:2]
            else:
                # A pair may spawn if at least one farmer remains to work.
                nonfarmers = [c for c in available if self._role(c) != "farmer"]
                if len(farmers) >= 1 and len(nonfarmers) >= 1:
                    spawn_pair = [farmers[0], nonfarmers[0]]

        # Once two warrior spawns have been requested, also make sure to
        # produce at least one farmer when the food reserve allows it.
        if (
            spawn_pair is None
            and not self._farmer_spawned
            and self._warrior_spawned >= 2
            and wheat >= 10
            and len(farmers) >= 3
        ):
            spawn_pair = farmers[:2]
            spawn_group = "spawn farmer"
        else:
            spawn_group = "spawn warrior"

        if spawn_pair is not None:
            for component in spawn_pair:
                self._assign(environment, component, spawn_group, group_ids)
                assigned.add(id(component))
            if spawn_group == "spawn warrior":
                self._warrior_spawned += 1
            else:
                self._farmer_spawned = True

        dragon_alive = environment.dragon.hp > 0

        # Explicitly assign every remaining villager. Healthy warriors move
        # promptly to the Cave; farmers stay and replenish the food supply.
        for component in components:
            if id(component) in assigned:
                continue

            if not dragon_alive:
                group = "farm"
            elif self._role(component) == "farmer":
                group = "farm"
            elif component.steps_since_meal >= 4:
                # Eat in the Village before undertaking the trip to the Cave.
                group = "eat" if wheat > 0 else "farm"
                if group == "eat":
                    wheat -= 1
            else:
                group = "cave"

            self._assign(environment, component, group, group_ids)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        dragon_alive = environment.dragon.hp > 0

        for component in components:
            if not dragon_alive:
                group = "village"
            elif self._role(component) != "warrior":
                group = "village"
            elif component.steps_since_meal >= 5:
                # Return with enough time to reach the Village and eat.
                group = "village"
            else:
                # Keep pressure on the Dragon to limit its regeneration.
                group = "attack"

            self._assign(environment, component, group, group_ids)