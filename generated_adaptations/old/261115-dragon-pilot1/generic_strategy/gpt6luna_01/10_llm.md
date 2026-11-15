The main opportunity to improve is to spend less time on optional Farmer spawning and get Warriors attacking sooner. This policy keeps at least one Farmer farming when possible, uses other eligible pairs to spawn Warriors, and feeds villagers only as they approach the starvation threshold. In the Cave, it staggers returns at four steps since a meal, but sends critically overdue Warriors back rather than letting starvation disable their attacks.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        assignments = {}
        wheat = max(0, int(environment.farm.wheat))

        # Feed villagers nearing starvation, prioritizing Warriors so they
        # can resume attacking. Keep some wheat available for spawn actions.
        hungry = [c for c in components if c.steps_since_meal >= 5]
        hungry.sort(
            key=lambda c: (c.role == "Warrior", c.steps_since_meal),
            reverse=True,
        )
        for c in hungry[:wheat]:
            assignments[id(c)] = "eat"

        wheat_left = wheat - sum(
            1 for c in components if assignments.get(id(c)) == "eat"
        )

        # Spawn Warriors rather than spending wheat on optional Farmer
        # batches. Prefer pairs of Farmers when that leaves a Farmer farming;
        # otherwise use a pair of available villagers if one is available.
        while wheat_left >= 12:
            available = [c for c in components if id(c) not in assignments]
            farmers = [c for c in available if c.role == "Farmer"]

            if len(farmers) >= 3:
                pair = farmers[:2]
            else:
                pair = available[:2]

            if len(pair) < 2:
                break

            for c in pair:
                assignments[id(c)] = "spawn warrior"
            wheat_left -= 12

        # Keep Farmers producing wheat. Fed Warriors travel to the Cave;
        # hungry ones remain in the Village until they can eat.
        for c in components:
            if id(c) in assignments:
                continue
            if c.role == "Warrior" and c.steps_since_meal >= 5:
                assignments[id(c)] = "farm"
            else:
                assignments[id(c)] = "cave" if c.role == "Warrior" else "farm"

        for c in components:
            environment.assign_group(c, assignments[id(c)])

    def assign_in_cave(self, components, environment, group_ids, step: int):
        assignments = {}
        warriors = [c for c in components if c.role == "Warrior"]

        for c in components:
            if c.role != "Warrior":
                assignments[id(c)] = "village"

        # Critically overdue Warriors return. At age four, stagger returns
        # while keeping at least one Warrior attacking whenever possible.
        overdue = [c for c in warriors if c.steps_since_meal >= 5]
        for c in overdue:
            assignments[id(c)] = "village"

        remaining = [c for c in warriors if id(c) not in assignments]
        due = sorted(
            [c for c in remaining if c.steps_since_meal >= 4],
            key=lambda c: c.steps_since_meal,
            reverse=True,
        )

        if due:
            return_count = 1 if len(remaining) > 1 else len(remaining)
            for c in due[:return_count]:
                assignments[id(c)] = "village"

        for c in warriors:
            if id(c) not in assignments:
                assignments[id(c)] = "attack"

        for c in components:
            environment.assign_group(c, assignments[id(c)])
```