The earlier policy capped Warrior spawning at two, which is unlikely to provide enough damage before the turn limit. This version keeps producing Warriors whenever wheat and a pair of villagers allow it, while reserving wheat for meals first. It also gives Farmers priority for producing food, adds up to two Farmer batches only when there is a surplus, and staggers Warriors’ meal trips so an attacker can remain in the Cave when possible. Every villager is explicitly assigned each call.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._farmer_batches = 0

    def assign_in_village(self, components, environment, group_ids, step: int):
        assignments = {}
        wheat = max(0, int(environment.farm.wheat))
        dragon_alive = environment.dragon.hp > 0

        # Eat before spending wheat on spawns. Feed the most overdue first;
        # Warriors break ties to get them back to the Cave sooner.
        hungry = [c for c in components if c.steps_since_meal >= 4]
        hungry.sort(
            key=lambda c: (c.steps_since_meal, c.role == "Warrior"),
            reverse=True,
        )
        for c in hungry[:wheat]:
            assignments[id(c)] = "eat"

        wheat_left = wheat - sum(
            1 for c in components if assignments.get(id(c)) == "eat"
        )
        available = [c for c in components if id(c) not in assignments]

        # Repeatedly spawn Warriors when possible rather than stopping after
        # the first two. A pair can be used again on later steps.
        farmer_pair = [c for c in available if c.role == "Farmer"][:2]
        if dragon_alive and step < 25 and wheat_left >= 12 and len(farmer_pair) == 2:
            for c in farmer_pair:
                assignments[id(c)] = "spawn warrior"
            wheat_left -= 12

        # Add a small number of Farmers when the food reserve is ample.
        # This is secondary to spawning Warriors.
        remaining = [c for c in available if id(c) not in assignments]
        farmer_pair = [c for c in remaining if c.role == "Farmer"][:2]
        if (
            self._farmer_batches < 2
            and wheat_left >= 24
            and len(farmer_pair) == 2
        ):
            for c in farmer_pair:
                assignments[id(c)] = "spawn farmer"
            self._farmer_batches += 1

        # Keep Farmers producing food. Send fed Warriors to the Cave; leave
        # Warriors who are too hungry in the Village until they can eat.
        for c in components:
            if id(c) in assignments:
                continue
            if c.role == "Warrior":
                assignments[id(c)] = (
                    "farm" if c.steps_since_meal >= 5 else "cave"
                )
            else:
                assignments[id(c)] = "farm"

        for c in components:
            environment.assign_group(c, assignments[id(c)])

    def assign_in_cave(self, components, environment, group_ids, step: int):
        assignments = {}
        warriors = [c for c in components if c.role == "Warrior"]

        # Send any Farmers back to the Village.
        for c in components:
            if c.role != "Warrior":
                assignments[id(c)] = "village"

        # A Warrior should head back before starvation. Stagger returns,
        # keeping at least one Warrior attacking whenever possible.
        forced = [c for c in warriors if c.steps_since_meal >= 5]
        for c in forced:
            assignments[id(c)] = "village"

        remaining = [c for c in warriors if id(c) not in assignments]
        due = [c for c in remaining if c.steps_since_meal >= 4]
        due.sort(key=lambda c: c.steps_since_meal, reverse=True)

        # Return one at a time if there are multiple Warriors available;
        # if only one remains, send it for food rather than risk starvation.
        if due:
            return_count = len(due) if len(remaining) <= 1 else 1
            for c in due[:return_count]:
                assignments[id(c)] = "village"

        for c in warriors:
            if id(c) not in assignments:
                assignments[id(c)] = "attack"

        for c in components:
            environment.assign_group(c, assignments[id(c)])
```