from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        assignments = {}
        wheat = max(0, int(environment.farm.wheat))

        # Feed before spending wheat on spawning. Feed Warriors first, since
        # they can return to attacking after eating.
        hungry = [
            c for c in components
            if c.steps_since_meal >= (4 if c.role == "Warrior" else 5)
        ]
        hungry.sort(
            key=lambda c: (c.role == "Warrior", c.steps_since_meal),
            reverse=True,
        )
        for c in hungry[:wheat]:
            assignments[id(c)] = "eat"

        wheat_left = wheat - sum(
            1 for c in components if assignments.get(id(c)) == "eat"
        )

        # Spawn Warriors with Farmer pairs. When there are extra Farmers,
        # leave at least two available to keep producing food.
        while wheat_left >= 12:
            available_farmers = [
                c for c in components
                if c.role == "Farmer" and id(c) not in assignments
            ]

            if len(available_farmers) >= 4:
                pair = available_farmers[:2]
            elif len(available_farmers) >= 2:
                pair = available_farmers[:2]
            else:
                break

            for c in pair:
                assignments[id(c)] = "spawn warrior"
            wheat_left -= 12

        # Farmers work the farm. Warriors who have eaten recently head to
        # the Cave; hungry Warriors stay in the Village until fed.
        for c in components:
            if id(c) in assignments:
                continue
            if c.role == "Warrior":
                if c.steps_since_meal >= 4:
                    assignments[id(c)] = "farm"
                else:
                    assignments[id(c)] = "cave"
            else:
                assignments[id(c)] = "farm"

        for c in components:
            environment.assign_group(c, assignments[id(c)])

    def assign_in_cave(self, components, environment, group_ids, step: int):
        assignments = {}
        warriors = [c for c in components if c.role == "Warrior"]

        for c in components:
            if c.role != "Warrior":
                assignments[id(c)] = "village"

        # Critically overdue Warriors return, but preserve fresh attackers.
        overdue = sorted(
            [c for c in warriors if c.steps_since_meal >= 5],
            key=lambda c: c.steps_since_meal,
            reverse=True,
        )
        for c in overdue:
            assignments[id(c)] = "village"

        remaining = [c for c in warriors if id(c) not in assignments]

        # Stagger the earlier meal trips, keeping at least one Warrior
        # attacking whenever there is more than one available.
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