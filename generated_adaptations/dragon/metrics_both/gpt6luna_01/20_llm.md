The earlier strategies either conserved too much wheat or switched to Warrior spawns before establishing enough farming capacity. This version aims for a six-Farmer workforce (and at least two Farmer spawn requests), then spends available wheat on Warrior spawns while keeping Farmers farming whenever possible. Warriors are sent to the Cave immediately and assigned to attack every update.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._initial_farmers = None
        self._farmer_spawn_requests = 0

    @staticmethod
    def _is_warrior(component):
        return "warrior" in str(getattr(component, "role", "")).lower()

    def assign_in_village(self, components, environment, group_ids, step: int):
        farmers = []

        for component in components:
            if self._is_warrior(component):
                environment.assign_group(component, "cave")
            else:
                farmers.append(component)
                environment.assign_group(component, "farm")

        if self._initial_farmers is None:
            self._initial_farmers = len(farmers)

        if len(farmers) < 2 or getattr(environment.dragon, "hp", 1) <= 0:
            return

        wheat = max(0, getattr(environment.farm, "wheat", 0))

        # Build enough farming capacity to support sustained Warrior spawns,
        # while ensuring at least two Farmers are spawned.
        farmer_goal = max(6, self._initial_farmers + 2)
        if (
            self._farmer_spawn_requests < 2
            or (
                self._farmer_spawn_requests < farmer_goal - self._initial_farmers
                and len(farmers) < farmer_goal
            )
        ):
            if wheat < 10:
                return
            spawn_group = "spawn farmer"
            cost = 10
            pair = farmers[:2]
        else:
            # Use a pair for a Warrior spawn whenever affordable. Keep at
            # least two Farmers farming whenever the population allows it.
            if wheat < 12:
                return
            spawn_group = "spawn warrior"
            cost = 12

            if len(farmers) >= 4:
                pair = farmers[:2]
            else:
                pair = farmers[:2]

        if wheat < cost:
            return

        for farmer in pair:
            environment.assign_group(farmer, spawn_group)

        if spawn_group == "spawn farmer":
            self._farmer_spawn_requests += 1

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for component in components:
            if self._is_warrior(component):
                environment.assign_group(component, "attack")
            else:
                environment.assign_group(component, "village")
```