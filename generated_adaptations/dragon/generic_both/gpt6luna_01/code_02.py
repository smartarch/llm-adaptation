from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.spawned_farmers = 0
        self.spawned_warriors = 0
        self.ever_assigned_attack = False

    @staticmethod
    def _attr(component, name, default=0):
        return getattr(component, name, default)

    @staticmethod
    def _assign(environment, component, group_id):
        environment.assign_group(component, group_id)

    def assign_in_village(self, components, environment, group_ids, step: int):
        farmers = []
        warriors = []
        eaters = []

        for component in components:
            role = self._attr(component, "role", "")
            since_meal = self._attr(component, "steps_since_meal", 0)

            # Warriors should eat before their hunger makes the Cave trip
            # interfere with attacking. Farmers eat before reaching starvation.
            if role == "Warrior" and since_meal >= 3:
                eaters.append(component)
            elif role == "Farmer" and since_meal >= 5:
                eaters.append(component)
            elif role == "Farmer":
                farmers.append(component)
            elif role == "Warrior":
                warriors.append(component)
            else:
                # Unknown roles are kept safe in the Village and fed if needed.
                if since_meal >= 5:
                    eaters.append(component)
                else:
                    farmers.append(component)

        for component in eaters:
            self._assign(environment, component, "eat")

        # A spawn requires two villagers in its group. Prefer Farmers so that
        # Warriors remain available to attack or return for meals.
        spawn_group = None
        spawn_cost = 0
        if self.spawned_farmers < 2:
            spawn_group, spawn_cost = "spawn farmer", 10
        elif self.spawned_warriors < 2:
            spawn_group, spawn_cost = "spawn warrior", 12
        elif self.spawned_farmers < 2:
            spawn_group, spawn_cost = "spawn farmer", 10

        wheat = self._attr(environment.farm, "wheat", 0)
        candidates = list(farmers)

        # If there are not two non-hungry Farmers available, other villagers
        # may help spawn, but never take someone who needs to eat this step.
        if len(candidates) < 2:
            candidates.extend(warriors)

        if (
            spawn_group is not None
            and len(candidates) >= 2
            and wheat >= spawn_cost + len(eaters)
        ):
            self._assign(environment, candidates[0], spawn_group)
            self._assign(environment, candidates[1], spawn_group)

            if spawn_group == "spawn farmer":
                self.spawned_farmers += 1
            else:
                self.spawned_warriors += 1

            used = {id(candidates[0]), id(candidates[1])}
        else:
            used = set()

        for component in components:
            if component in eaters:
                continue
            if id(component) in used:
                continue

            role = self._attr(component, "role", "")
            since_meal = self._attr(component, "steps_since_meal", 0)

            if role == "Warrior" and since_meal < 3:
                self._assign(environment, component, "cave")
            else:
                # Farmers remain in the Village; Warriors not yet hungry
                # continue toward the Cave.
                self._assign(
                    environment,
                    component,
                    "cave" if role == "Warrior" else "farm",
                )

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for component in components:
            role = self._attr(component, "role", "")
            since_meal = self._attr(component, "steps_since_meal", 0)

            if role != "Warrior":
                self._assign(environment, component, "village")
            elif since_meal >= 4:
                # Returning at four steps without a meal allows the Warrior
                # to reach the Village and eat before starvation.
                self._assign(environment, component, "village")
            else:
                self._assign(environment, component, "attack")
                self.ever_assigned_attack = True