from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._farmer_spawn_assigned = False
        self._warrior_spawns_assigned = 0

    @staticmethod
    def _assign(environment, component, group):
        environment.assign_group(component, group)

    def assign_in_village(self, components, environment, group_ids, step: int):
        villagers = list(components)
        wheat = max(0, environment.farm.wheat)

        # Reserve a pair for each required spawn when possible. Prefer
        # recently fed farmers, so warriors can get to the Cave promptly.
        reserved = []
        spawn_group = None
        spawn_cost = 0

        if not self._farmer_spawn_assigned:
            spawn_group, spawn_cost = "spawn farmer", 10
        elif self._warrior_spawns_assigned < 2:
            spawn_group, spawn_cost = "spawn warrior", 12

        if spawn_group is not None and wheat >= spawn_cost:
            candidates = sorted(
                villagers,
                key=lambda c: (
                    c.steps_since_meal >= 5,
                    c.role != "Farmer",
                    c.steps_since_meal,
                ),
            )
            reserved = candidates[:2]
            if len(reserved) < 2:
                reserved = []

        if len(reserved) == 2:
            for c in reserved:
                self._assign(environment, c, spawn_group)
            if spawn_group == "spawn farmer":
                self._farmer_spawn_assigned = True
            else:
                self._warrior_spawns_assigned += 1

        reserved_ids = {id(c) for c in reserved}

        # Eat only when a villager is close to starving. Warriors eat in the
        # Village before departing; farmers remain productive unless urgent.
        eaters = []
        for c in villagers:
            if id(c) in reserved_ids:
                continue
            if c.steps_since_meal >= 5 and wheat > 0:
                eaters.append(c)
                wheat -= 1

        eater_ids = {id(c) for c in eaters}
        for c in eaters:
            self._assign(environment, c, "eat")

        for c in villagers:
            if id(c) in reserved_ids or id(c) in eater_ids:
                continue
            if c.role == "Farmer":
                self._assign(environment, c, "farm")
            else:
                # A warrior that is not due to eat should head to the Cave.
                self._assign(environment, c, "cave")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        dragon_alive = environment.dragon.hp > 0

        for c in components:
            if c.role == "Farmer":
                self._assign(environment, c, "village")
            elif not dragon_alive:
                self._assign(environment, c, "cave")
            elif c.steps_since_meal >= 4:
                # Leave before the hunger penalty disables attacks, allowing
                # a step to travel home and then eat.
                self._assign(environment, c, "village")
            else:
                self._assign(environment, c, "attack")