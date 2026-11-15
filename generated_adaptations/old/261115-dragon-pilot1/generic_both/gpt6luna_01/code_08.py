from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.farmers_spawned = 0

    @staticmethod
    def _get(component, name, default=0):
        return getattr(component, name, default)

    @staticmethod
    def _assign(environment, component, group):
        environment.assign_group(component, group)

    def assign_in_village(self, components, environment, group_ids, step: int):
        eaters = []
        farmers = []
        warriors = []

        for component in components:
            role = self._get(component, "role", "")
            hunger = self._get(component, "steps_since_meal", 0)

            if role == "Warrior":
                if hunger >= 3:
                    eaters.append(component)
                else:
                    warriors.append(component)
            elif role == "Farmer":
                if hunger >= 5:
                    eaters.append(component)
                else:
                    farmers.append(component)
            elif hunger >= 5:
                eaters.append(component)
            else:
                farmers.append(component)

        eater_ids = {id(component) for component in eaters}
        for component in eaters:
            self._assign(environment, component, "eat")

        wheat = self._get(environment.farm, "wheat", 0)
        food_reserve = len(eaters)

        # Establish two additional Farmers first. Then use available Farmers
        # to spawn Warriors, whose damage is more valuable against the Dragon.
        if self.farmers_spawned < 2:
            spawn_group = "spawn farmer"
            spawn_cost = 10
            candidates = farmers
        else:
            spawn_group = "spawn warrior"
            spawn_cost = 12
            candidates = farmers

        spawn_pair = []
        if len(candidates) >= 2:
            # Prefer leaving a Farmer working. If there are only two Farmers,
            # spawn with them only when the food stock can cover the pause in
            # farming as well as meals and the spawn cost.
            enough_farmers_to_spare = len(farmers) >= 3
            food_buffer = 0 if enough_farmers_to_spare else 10

            if wheat >= spawn_cost + food_reserve + food_buffer:
                spawn_pair = candidates[:2]

        spawned_ids = {id(component) for component in spawn_pair}
        for component in spawn_pair:
            self._assign(environment, component, spawn_group)

        if spawn_pair and spawn_group == "spawn farmer":
            self.farmers_spawned += 1

        for component in components:
            component_id = id(component)
            if component_id in eater_ids or component_id in spawned_ids:
                continue

            if self._get(component, "role", "") == "Warrior":
                self._assign(environment, component, "cave")
            else:
                self._assign(environment, component, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        warriors = [
            component
            for component in components
            if self._get(component, "role", "") == "Warrior"
        ]

        # At hunger 3, stagger some returns. Everyone remaining at hunger 4
        # heads back so they can eat in the Village before starvation.
        return_ids = set()
        for component in warriors:
            hunger = self._get(component, "steps_since_meal", 0)

            if hunger >= 4:
                return_ids.add(id(component))
            elif (
                hunger >= 3
                and len(warriors) > 1
                and id(component) % 3 == step % 3
            ):
                return_ids.add(id(component))

        for component in components:
            if id(component) in return_ids:
                self._assign(environment, component, "village")
            elif self._get(component, "role", "") == "Warrior":
                self._assign(environment, component, "attack")
            else:
                self._assign(environment, component, "village")