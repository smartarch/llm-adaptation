The strategy keeps farmers in the Village, uses them to spawn up to two Warriors and two Farmers when wheat and eligible pairs are available, and prioritizes meals before spawning. Warriors head to the Cave when fed; in the Cave, they attack unless it is time to return for food. To reduce attack gaps, the strategy staggers returns when possible and sends back anyone who is more overdue. Every component is explicitly assigned on every call. As with any assignment policy, the attack cadence cannot be guaranteed if there are too few living Warriors or too little wheat for meals.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._spawned_warriors = 0
        self._spawned_farmers = 0

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Eat before spawning or sending Warriors away. Reserve only as many
        # meals as the current wheat supply can pay for.
        wheat = max(0, int(environment.farm.wheat))
        due = [c for c in components if c.steps_since_meal >= 4]
        due.sort(
            key=lambda c: (
                c.steps_since_meal,
                c.role == "Warrior",
            ),
            reverse=True,
        )

        eaten = set()
        for component in due[:wheat]:
            environment.assign_group(component, "eat")
            eaten.add(id(component))

        available = [
            c for c in components
            if id(c) not in eaten and c.steps_since_meal < 4
        ]
        farmers = [c for c in available if c.role == "Farmer"]

        # Use farmer pairs for spawning where possible, so Warriors can get
        # to the Cave promptly. Spawn one pair per step.
        spawn_choice = None
        if self._spawned_warriors < 2 and wheat >= 12:
            spawn_choice = ("spawn warrior", 12)
        elif self._spawned_farmers < 2 and wheat >= 10:
            spawn_choice = ("spawn farmer", 10)

        if spawn_choice is not None:
            group, cost = spawn_choice
            workers = farmers[:2]

            # If there are not two eligible Farmers, use other eligible
            # villagers rather than leaving a viable spawn opportunity unused.
            if len(workers) < 2:
                others = [c for c in available if c not in workers]
                workers.extend(others[: 2 - len(workers)])

            if len(workers) == 2 and wheat >= cost:
                for component in workers:
                    environment.assign_group(component, group)
                if group == "spawn warrior":
                    self._spawned_warriors += 1
                else:
                    self._spawned_farmers += 1
                available = [c for c in available if c not in workers]

        # Farmers work the farm; Warriors stay in the Village if they need
        # food, otherwise they head to the Cave.
        for component in components:
            if id(component) in eaten:
                continue
            if component in available:
                if component.role == "Warrior":
                    if component.steps_since_meal < 4:
                        environment.assign_group(component, "cave")
                    else:
                        # Keep an unfed Warrior in the Village rather than
                        # sending them to the Cave too hungry to fight.
                        environment.assign_group(component, "farm")
                else:
                    environment.assign_group(component, "farm")
            else:
                # A component assigned to a spawn group has already been
                # assigned; this branch is only a defensive fallback.
                pass

    def assign_in_cave(self, components, environment, group_ids, step: int):
        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role != "Warrior"]

        # Any Farmers found in the Cave should return to the Village.
        for component in farmers:
            environment.assign_group(component, "village")

        overdue = [c for c in warriors if c.steps_since_meal >= 5]
        if overdue:
            # Do not leave a very hungry Warrior in the Cave.
            returning = set(id(c) for c in overdue)
        else:
            due = [c for c in warriors if c.steps_since_meal >= 4]
            # Stagger returns by sending only the most overdue Warrior first.
            due.sort(key=lambda c: c.steps_since_meal, reverse=True)
            returning = {id(due[0])} if due else set()

        for component in warriors:
            if id(component) in returning:
                environment.assign_group(component, "village")
            else:
                environment.assign_group(component, "attack")
```