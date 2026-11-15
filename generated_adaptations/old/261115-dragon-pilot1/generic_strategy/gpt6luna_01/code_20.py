from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        assignments = {}
        wheat = max(0, int(environment.farm.wheat))

        # Feed villagers before they reach starvation. Warriors get priority
        # so they can resume attacking quickly.
        hungry = [c for c in components if c.steps_since_meal >= 4]
        hungry.sort(
            key=lambda c: (c.role == "Warrior", c.steps_since_meal),
            reverse=True,
        )
        for c in hungry[:wheat]:
            assignments[id(c)] = "eat"

        wheat_left = wheat - sum(
            1 for c in components if assignments.get(id(c)) == "eat"
        )

        # Use Farmer pairs to create Warriors, while preserving food
        # production whenever possible.
        while wheat_left >= 12:
            available_farmers = [
                c for c in components
                if c.role == "Farmer" and id(c) not in assignments
            ]

            if len(available_farmers) >= 3:
                pair = available_farmers[:2]
            elif len(available_farmers) == 2 and wheat_left >= 24:
                pair = available_farmers
            else:
                break

            for c in pair:
                assignments[id(c)] = "spawn warrior"
            wheat_left -= 12

        # Add one Farmer batch only when there is surplus wheat and enough
        # Farmers to keep at least two working.
        farmer_count = sum(c.role == "Farmer" for c in components)
        available_farmers = [
            c for c in components
            if c.role == "Farmer" and id(c) not in assignments
        ]
        if (
            farmer_count < 4
            and wheat_left >= 10
            and len(available_farmers) >= 4
        ):
            for c in available_farmers[:2]:
                assignments[id(c)] = "spawn farmer"

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

        for c in components:
            if c.role != "Warrior":
                assignments[id(c)] = "village"

        # If the Dragon can be killed by this turn's available attacks,
        # prioritize finishing it over taking a meal trip.
        attack_ready = [
            c for c in warriors if c.steps_since_meal < 6 and c.hp > 0
        ]
        if environment.dragon.hp <= 3 * len(attack_ready):
            for c in warriors:
                if c.steps_since_meal < 6:
                    assignments[id(c)] = "attack"
                else:
                    assignments[id(c)] = "village"
        else:
            # Return critically overdue Warriors; fresher Warriors keep
            # attacking. At four steps, stagger meal trips one at a time.
            for c in warriors:
                if c.steps_since_meal >= 6:
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