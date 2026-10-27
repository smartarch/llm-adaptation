from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.farmers_spawned = 0
        self.warriors_spawned = 0

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
                # Eat in the Village before starting another Cave trip.
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

        for component in eaters:
            self._assign(environment, component, "eat")

        wheat = self._get(environment.farm, "wheat", 0)
        eat_cost = len(eaters)

        # First establish a small Farmer reserve. After that, use surplus
        # Farmers to produce Warriors while leaving Farmers to keep farming.
        spawn_group = None
        spawn_cost = 0
        if self.farmers_spawned < 2:
            spawn_group, spawn_cost = "spawn farmer", 10
        elif self.warriors_spawned < 2:
            spawn_group, spawn_cost = "spawn warrior", 12
        else:
            spawn_group, spawn_cost = "spawn warrior", 12

        available_farmers = list(farmers)
        if spawn_group == "spawn farmer":
            # Allow the initial pair to bootstrap the Farmer population.
            spawn_candidates = available_farmers
        else:
            # Keep at least two Farmers working when possible.
            spawn_candidates = (
                available_farmers
                if len(available_farmers) >= 3
                else []
            )

        used_ids = set()
        if (
            len(spawn_candidates) >= 2
            and wheat >= spawn_cost + eat_cost + 2
        ):
            pair = spawn_candidates[:2]
            for component in pair:
                self._assign(environment, component, spawn_group)
                used_ids.add(id(component))

            if spawn_group == "spawn farmer":
                self.farmers_spawned += 1
            else:
                self.warriors_spawned += 1

        for component in components:
            if id(component) in used_ids or any(
                component is eater for eater in eaters
            ):
                continue

            role = self._get(component, "role", "")
            if role == "Warrior":
                self._assign(environment, component, "cave")
            else:
                self._assign(environment, component, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        warriors = [
            component
            for component in components
            if self._get(component, "role", "") == "Warrior"
        ]

        # Hunger-based departures are spread across three buckets. If a
        # Warrior is close to starvation, food takes priority over staggering.
        departures = []
        for component in warriors:
            hunger = self._get(component, "steps_since_meal", 0)
            phase = id(component) % 3
            scheduled = (step + phase) % 3 == 0

            if hunger >= 5 or (hunger >= 3 and scheduled):
                departures.append(component)

        # Preserve an attacker whenever possible, preventing avoidable Dragon
        # regeneration when several Warriors are available.
        if len(warriors) > 1 and len(departures) == len(warriors):
            keep_attacking = min(
                departures,
                key=lambda component: self._get(
                    component, "steps_since_meal", 0
                ),
            )
            departures.remove(keep_attacking)

        departure_ids = {id(component) for component in departures}
        for component in components:
            if id(component) in departure_ids:
                self._assign(environment, component, "village")
            elif self._get(component, "role", "") == "Warrior":
                self._assign(environment, component, "attack")
            else:
                self._assign(environment, component, "village")