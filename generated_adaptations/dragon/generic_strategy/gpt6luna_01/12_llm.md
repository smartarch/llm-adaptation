To improve on the previous policy, I’d avoid using Warriors as spawners: they should spend their time reaching and attacking the Dragon. This version spends available spawn wheat on Warrior batches using Farmers, keeps a Farmer working when the roster allows it, and feeds Warriors in the Village before sending them back to the Cave. Cave returns are staggered at four steps without a meal when possible, so the group keeps attacking while someone goes for food.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        assignments = {}
        wheat = max(0, int(environment.farm.wheat))

        # Feed villagers before they starve. Warriors get priority so they
        # can return to the Cave promptly after eating.
        hungry = [
            c for c in components
            if c.steps_since_meal >= (4 if c.role == "Warrior" else 5)
        ]
        hungry.sort(
            key=lambda c: (
                c.role == "Warrior",
                c.steps_since_meal,
            ),
            reverse=True,
        )
        for c in hungry[:wheat]:
            assignments[id(c)] = "eat"

        wheat_left = wheat - sum(
            1 for c in components if assignments.get(id(c)) == "eat"
        )

        # Use Farmers, not Warriors, as spawners. Keep one Farmer available
        # to work whenever there are enough Farmers to do so.
        while wheat_left >= 12:
            available_farmers = [
                c for c in components
                if c.role == "Farmer" and id(c) not in assignments
            ]

            if len(available_farmers) >= 3:
                pair = available_farmers[:2]
            elif len(available_farmers) == 2:
                pair = available_farmers
            else:
                break

            for c in pair:
                assignments[id(c)] = "spawn warrior"
            wheat_left -= 12

        # Unassigned Farmers farm. Fed Warriors go to the Cave; Warriors
        # who need food remain in the Village rather than travelling hungry.
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

        # Any Farmers in the Cave should return to the Village.
        for c in components:
            if c.role != "Warrior":
                assignments[id(c)] = "village"

        # At five steps without a meal, send overdue Warriors back to avoid
        # further starvation. Under that threshold, stagger one return at a
        # time so other Warriors can keep attacking.
        overdue = sorted(
            [c for c in warriors if c.steps_since_meal >= 5],
            key=lambda c: c.steps_since_meal,
            reverse=True,
        )

        if overdue:
            for c in overdue:
                assignments[id(c)] = "village"
        else:
            due = sorted(
                [c for c in warriors if c.steps_since_meal >= 4],
                key=lambda c: c.steps_since_meal,
                reverse=True,
            )
            if due:
                return_count = 1 if len(warriors) > 1 else len(warriors)
                for c in due[:return_count]:
                    assignments[id(c)] = "village"

        for c in warriors:
            if id(c) not in assignments:
                assignments[id(c)] = "attack"

        for c in components:
            environment.assign_group(c, assignments[id(c)])
```