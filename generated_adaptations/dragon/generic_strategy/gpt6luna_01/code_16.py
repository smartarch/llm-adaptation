from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        assignments = {}
        wheat = max(0, int(environment.farm.wheat))

        # Feed overdue villagers first; prioritize Warriors so they can
        # resume attacking. Save any remaining wheat for spawns.
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
        available_farmers = [
            c for c in components
            if c.role == "Farmer" and id(c) not in assignments
        ]

        # An early Farmer batch increases food production, helping sustain
        # a larger Warrior force. Aim for four Farmers.
        total_farmers = sum(c.role == "Farmer" for c in components)
        if total_farmers < 4 and wheat_left >= 10 and len(available_farmers) >= 2:
            for c in available_farmers[:2]:
                assignments[id(c)] = "spawn farmer"
            wheat_left -= 10

        # Spawn at most one Warrior batch per turn to stagger meal schedules.
        available_farmers = [
            c for c in components
            if c.role == "Farmer" and id(c) not in assignments
        ]
        if wheat_left >= 12 and len(available_farmers) >= 4:
            for c in available_farmers[:2]:
                assignments[id(c)] = "spawn warrior"

        # Farmers not spawning keep working. Warriors in the Village eat
        # when overdue, otherwise they head back to the Cave.
        for c in components:
            if id(c) in assignments:
                continue
            if c.role == "Warrior" and c.steps_since_meal >= 5:
                assignments[id(c)] = "farm"
            elif c.role == "Warrior":
                assignments[id(c)] = "cave"
            else:
                assignments[id(c)] = "farm"

        for c in components:
            environment.assign_group(c, assignments[id(c)])

    def assign_in_cave(self, components, environment, group_ids, step: int):
        assignments = {}
        warriors = [c for c in components if c.role == "Warrior"]

        # Send any Farmers in the Cave back to the Village.
        for c in components:
            if c.role != "Warrior":
                assignments[id(c)] = "village"

        # Return critically overdue Warriors. Otherwise, stagger meal trips:
        # send only the most overdue Warrior while others continue attacking.
        critically_overdue = sorted(
            (c for c in warriors if c.steps_since_meal >= 6),
            key=lambda c: c.steps_since_meal,
            reverse=True,
        )
        for c in critically_overdue:
            assignments[id(c)] = "village"

        remaining = [c for c in warriors if id(c) not in assignments]
        due = sorted(
            (c for c in remaining if c.steps_since_meal >= 5),
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