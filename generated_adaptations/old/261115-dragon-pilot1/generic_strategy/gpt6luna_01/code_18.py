from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        assignments = {}
        wheat = max(0, int(environment.farm.wheat))

        # Eat before spawning. Warriors have priority so they can return
        # to the Cave; farmers eat too when they are near starvation.
        hungry = [
            c for c in components
            if c.steps_since_meal >= 4
        ]
        hungry.sort(
            key=lambda c: (c.steps_since_meal, c.role == "Warrior"),
            reverse=True,
        )
        for c in hungry[:wheat]:
            assignments[id(c)] = "eat"

        wheat_left = wheat - sum(
            1 for c in components if assignments.get(id(c)) == "eat"
        )

        # Grow the farming base if it is small. This improves the food
        # supply for the larger Warrior force needed later.
        farmers = [
            c for c in components
            if c.role == "Farmer" and id(c) not in assignments
        ]
        farmer_count = sum(c.role == "Farmer" for c in components)

        if farmer_count < 4 and wheat_left >= 10 and len(farmers) >= 2:
            for c in farmers[:2]:
                assignments[id(c)] = "spawn farmer"
            wheat_left -= 10

        # Spawn one Warrior pair per turn, preserving two Farmers to work
        # when possible. If there are only two Farmers, use them when wheat
        # is sufficient; the spawn is worth one temporarily reduced farm turn.
        farmers = [
            c for c in components
            if c.role == "Farmer" and id(c) not in assignments
        ]
        if wheat_left >= 12 and len(farmers) >= 2:
            if len(farmers) >= 4 or wheat_left >= 24:
                for c in farmers[:2]:
                    assignments[id(c)] = "spawn warrior"

        # Assign everyone not eating or spawning. Farmers farm, while fed
        # Warriors head for the Cave.
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

        # Farmers should return to the Village.
        for c in components:
            if c.role != "Warrior":
                assignments[id(c)] = "village"

        # Return Warriors at four steps without food, one at a time where
        # possible. At six steps, anyone still in the Cave is starving and
        # should return; retain an attacker only if one can still fight.
        overdue = sorted(
            (c for c in warriors if c.steps_since_meal >= 6),
            key=lambda c: c.steps_since_meal,
            reverse=True,
        )
        for c in overdue:
            assignments[id(c)] = "village"

        remaining = [c for c in warriors if id(c) not in assignments]
        due = sorted(
            (c for c in remaining if c.steps_since_meal >= 4),
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