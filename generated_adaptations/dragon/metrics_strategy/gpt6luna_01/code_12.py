from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.warrior_spawn_requests = 0
        self.farmer_spawn_requests = 0

    @staticmethod
    def assign(environment, component, group):
        environment.assign_group(component, group)

    def assign_in_village(self, components, environment, group_ids, step: int):
        farmers = []
        meals_assigned = 0

        for component in components:
            if component.role == "Warrior":
                # Eat on arrival when hungry; otherwise head back to the Cave.
                if component.steps_since_meal >= 3:
                    self.assign(environment, component, "eat")
                    meals_assigned += 1
                else:
                    self.assign(environment, component, "cave")
            elif component.steps_since_meal >= 5:
                self.assign(environment, component, "eat")
                meals_assigned += 1
            else:
                farmers.append(component)

        wheat_available = max(
            0, environment.farm.wheat - meals_assigned - 2
        )

        # Create the requested Warriors first, then Farmers if resources allow.
        spawn_plans = []
        if self.warrior_spawn_requests < 2:
            spawn_plans.append(("spawn warrior", 12, "warrior"))
        if self.farmer_spawn_requests < 2:
            spawn_plans.append(("spawn farmer", 10, "farmer"))

        for group, cost, kind in spawn_plans:
            if len(farmers) < 2 or wheat_available < cost:
                continue

            pair = farmers[:2]
            farmers = farmers[2:]
            for component in pair:
                self.assign(environment, component, group)

            wheat_available -= cost
            if kind == "warrior":
                self.warrior_spawn_requests += 1
            else:
                self.farmer_spawn_requests += 1

        for component in farmers:
            self.assign(environment, component, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        warriors = []

        for component in components:
            if component.role == "Warrior":
                warriors.append(component)
            else:
                self.assign(environment, component, "village")

        # Start meal trips at hunger 3, staggering departures. Anyone at 4
        # returns immediately so the travel and meal can happen before starvation.
        for index, component in enumerate(warriors):
            hunger = component.steps_since_meal
            return_to_village = (
                hunger >= 4
                or (hunger >= 3 and (index + step) % 2 == 0)
            )

            if return_to_village:
                self.assign(environment, component, "village")
            else:
                self.assign(environment, component, "attack")