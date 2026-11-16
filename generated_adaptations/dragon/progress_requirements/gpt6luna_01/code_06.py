from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.farmer_spawn_assigned = False

    @staticmethod
    def _assign(environment, component, group):
        environment.assign_group(component, group)

    def assign_in_village(self, components, environment, group_ids, step: int):
        villagers = list(components)
        wheat = max(0, environment.farm.wheat)

        # Eat before the starvation threshold. Prioritize the hungriest
        # villagers, while reserving enough wheat for any meal assignments.
        eaters = []
        for c in sorted(villagers, key=lambda x: x.steps_since_meal, reverse=True):
            if c.steps_since_meal >= 5 and len(eaters) < wheat:
                eaters.append(c)

        for c in eaters:
            self._assign(environment, c, "eat")

        remaining_wheat = wheat - len(eaters)
        eater_ids = {id(c) for c in eaters}

        farmers = [
            c for c in villagers
            if c.role == "Farmer" and id(c) not in eater_ids
        ]
        farmers.sort(key=lambda c: c.steps_since_meal)

        spawn_group = None
        cost = 0
        if not self.farmer_spawn_assigned:
            spawn_group, cost = "spawn farmer", 10
        else:
            # Continue producing warriors rather than stopping after the
            # minimum required number.
            spawn_group, cost = "spawn warrior", 12

        spawn_workers = []
        if remaining_wheat >= cost and len(farmers) >= 2:
            spawn_workers = farmers[:2]

        spawn_worker_ids = {id(c) for c in spawn_workers}
        if spawn_workers:
            for c in spawn_workers:
                self._assign(environment, c, spawn_group)
            if spawn_group == "spawn farmer":
                self.farmer_spawn_assigned = True

        for c in villagers:
            if id(c) in eater_ids or id(c) in spawn_worker_ids:
                continue
            if c.role == "Farmer":
                self._assign(environment, c, "farm")
            elif c.steps_since_meal >= 5:
                # If wheat was unavailable above, keep a hungry warrior in
                # the Village rather than send them out unable to fight.
                self._assign(environment, c, "eat")
            else:
                self._assign(environment, c, "cave")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.role == "Farmer":
                self._assign(environment, c, "village")
            elif environment.dragon.hp <= 0:
                self._assign(environment, c, "cave")
            elif c.steps_since_meal >= 4:
                # Travel home at four steps since eating, then eat in the
                # Village before the starvation threshold.
                self._assign(environment, c, "village")
            else:
                self._assign(environment, c, "attack")