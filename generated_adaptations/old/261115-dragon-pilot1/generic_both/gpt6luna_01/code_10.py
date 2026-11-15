from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.farmer_spawn_events = 0

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
        meal_reserve = len(eaters)

        # Spawn one pair of Farmers, then spend surplus food on Warriors.
        if self.farmer_spawn_events < 1:
            spawn_group = "spawn farmer"
            spawn_cost = 10
        else:
            spawn_group = "spawn warrior"
            spawn_cost = 12

        spawn_pair = []
        if len(farmers) >= 2:
            # Keep at least one Farmer farming when possible. With only two
            # Farmers, spawn only when there is a substantial food reserve.
            food_buffer = 0 if len(farmers) >= 3 else 10
            if wheat >= spawn_cost + meal_reserve + food_buffer:
                spawn_pair = farmers[:2]

        spawned_ids = {id(component) for component in spawn_pair}
        for component in spawn_pair:
            self._assign(environment, component, spawn_group)

        if spawn_pair and spawn_group == "spawn farmer":
            self.farmer_spawn_events += 1

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

        returning_ids = set()
        for component in warriors:
            hunger = self._get(component, "steps_since_meal", 0)

            # Spread some trips back to the Village across hunger level 3.
            # Any Warriors still in the Cave return by level 4.
            if hunger >= 4:
                returning_ids.add(id(component))
            elif hunger >= 3 and len(warriors) > 1:
                if (id(component) + step) % 2 == 0:
                    returning_ids.add(id(component))

        for component in components:
            if self._get(component, "role", "") != "Warrior":
                self._assign(environment, component, "village")
            elif id(component) in returning_ids:
                self._assign(environment, component, "village")
            else:
                self._assign(environment, component, "attack")