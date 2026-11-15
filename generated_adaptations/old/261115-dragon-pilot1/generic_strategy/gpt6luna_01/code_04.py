from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._warriors_spawned = 0
        self._farmers_spawned = 0

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = max(0, int(environment.farm.wheat))
        assignments = {}
        eaten = set()
        used_for_spawning = set()

        # Feed the hungriest first, favoring Warriors so they can keep fighting.
        hungry = [c for c in components if c.steps_since_meal >= 4]
        hungry.sort(
            key=lambda c: (
                c.steps_since_meal,
                c.role == "Warrior",
            ),
            reverse=True,
        )
        for c in hungry[:wheat]:
            assignments[id(c)] = "eat"
            eaten.add(id(c))

        wheat_left = wheat - len(eaten)
        eligible_farmers = [
            c for c in components
            if c.role == "Farmer"
            and id(c) not in eaten
            and c.steps_since_meal < 5
        ]

        # Prefer Warriors for the Cave, and spawn no more than two of each
        # type. Each spawn consumes a pair of villagers and the listed wheat.
        while self._warriors_spawned < 2 and wheat_left >= 12:
            pair = eligible_farmers[:2]
            if len(pair) < 2:
                break
            for c in pair:
                assignments[id(c)] = "spawn warrior"
                used_for_spawning.add(id(c))
                eligible_farmers.remove(c)
            self._warriors_spawned += 1
            wheat_left -= 12

        while self._farmers_spawned < 2 and wheat_left >= 10:
            pair = eligible_farmers[:2]
            if len(pair) < 2:
                break
            for c in pair:
                assignments[id(c)] = "spawn farmer"
                used_for_spawning.add(id(c))
                eligible_farmers.remove(c)
            self._farmers_spawned += 1
            wheat_left -= 10

        for c in components:
            if id(c) in assignments:
                continue

            if c.role == "Warrior":
                # Do not send an unfed Warrior to the Cave if they are
                # approaching starvation.
                if c.steps_since_meal >= 5:
                    assignments[id(c)] = "farm"
                else:
                    assignments[id(c)] = "cave"
            else:
                assignments[id(c)] = "farm"

        for c in components:
            environment.assign_group(c, assignments[id(c)])

    def assign_in_cave(self, components, environment, group_ids, step: int):
        warriors = [c for c in components if c.role == "Warrior"]
        assignments = {}

        # Farmers should not be in the Cave.
        for c in components:
            if c.role != "Warrior":
                assignments[id(c)] = "village"

        # A Warrior at 5+ steps without food must return. Otherwise, stagger
        # voluntary returns and keep at least one Warrior attacking whenever
        # possible.
        forced_returns = {
            id(c) for c in warriors if c.steps_since_meal >= 5
        }
        for c in warriors:
            if id(c) in forced_returns:
                assignments[id(c)] = "village"

        remaining = [
            c for c in warriors if id(c) not in forced_returns
        ]
        voluntary_due = [c for c in remaining if c.steps_since_meal >= 3]
        voluntary_due.sort(key=lambda c: c.steps_since_meal, reverse=True)

        # Leave at least one Warrior in the Cave to attack.
        return_count = min(len(voluntary_due), max(0, len(remaining) - 1))
        for c in voluntary_due[:return_count]:
            assignments[id(c)] = "village"

        for c in warriors:
            if id(c) not in assignments:
                assignments[id(c)] = "attack"

        for c in components:
            environment.assign_group(c, assignments[id(c)])