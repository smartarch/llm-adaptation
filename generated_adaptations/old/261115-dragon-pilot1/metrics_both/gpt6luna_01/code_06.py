from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._next_rank = 0
        self._ranks = {}
        self._spawned = {"spawn warrior": 0, "spawn farmer": 0}
        self._newly_sent_to_cave = set()

    @staticmethod
    def _role(component):
        # Accommodate either plain strings or enum-like role values.
        return str(component.role).lower().split(".")[-1]

    @staticmethod
    def _assign(environment, component, group):
        environment.assign_group(component, group)

    def _rank(self, component):
        key = id(component)
        if key not in self._ranks:
            self._ranks[key] = self._next_rank
            self._next_rank += 1
        return self._ranks[key]

    def assign_in_village(self, components, environment, group_ids, step: int):
        warriors = []
        farmers = []

        for component in components:
            if self._role(component) == "warrior":
                self._rank(component)
                warriors.append(component)
            else:
                farmers.append(component)

        assigned = set()
        wheat = max(0, environment.farm.wheat)

        # Warriors eat in the Village before they get too hungry to make the
        # trip to the Cave and attack. Farmers eat before reaching starvation.
        for component in warriors:
            if component.steps_since_meal >= 3 and wheat > 0:
                self._assign(environment, component, "eat")
                assigned.add(id(component))
                wheat -= 1

        for component in farmers:
            if component.steps_since_meal >= 5 and wheat > 0:
                self._assign(environment, component, "eat")
                assigned.add(id(component))
                wheat -= 1

        # Preserve meals for Farmers who will soon need to eat.
        meal_reserve = sum(
            1 for farmer in farmers
            if id(farmer) not in assigned and farmer.steps_since_meal >= 4
        )
        spawn_wheat = max(0, wheat - meal_reserve)

        spawn_candidates = [
            farmer for farmer in farmers if id(farmer) not in assigned
        ]
        spawn_candidates.sort(
            key=lambda c: (c.steps_since_meal, -c.hp)
        )

        # Spawn at least two of each type when there are enough Farmers and
        # wheat. Each spawn assignment uses a pair of villagers.
        while len(spawn_candidates) >= 2:
            outstanding = [
                name for name in ("spawn warrior", "spawn farmer")
                if self._spawned[name] < 2
            ]
            if not outstanding:
                break

            # Prioritize Warriors to increase Dragon damage.
            name = min(
                outstanding,
                key=lambda n: (
                    self._spawned[n],
                    0 if n == "spawn warrior" else 1,
                ),
            )
            cost = 12 if name == "spawn warrior" else 10
            if spawn_wheat < cost:
                break

            pair = spawn_candidates[:2]
            spawn_candidates = spawn_candidates[2:]
            for component in pair:
                self._assign(environment, component, name)
                assigned.add(id(component))

            self._spawned[name] += 1
            spawn_wheat -= cost

        # Explicitly assign every remaining villager.
        for component in components:
            if id(component) in assigned:
                continue

            if self._role(component) == "warrior":
                self._assign(environment, component, "cave")
                self._newly_sent_to_cave.add(id(component))
            else:
                self._assign(environment, component, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        warriors = []

        for component in components:
            if self._role(component) != "warrior":
                self._assign(environment, component, "village")
                continue
            warriors.append(component)

        # Make every Warrior attack at least once after entering the Cave.
        newly_arrived = set()
        for component in warriors:
            key = id(component)
            if key in self._newly_sent_to_cave:
                newly_arrived.add(key)
                self._newly_sent_to_cave.discard(key)
                self._assign(environment, component, "attack")

        for component in warriors:
            if id(component) in newly_arrived:
                continue

            # Different cohorts return at different hunger levels. This
            # creates opportunities for another cohort to keep attacking.
            threshold = 3 if self._rank(component) % 2 == 0 else 4
            if component.steps_since_meal >= threshold:
                self._assign(environment, component, "village")
            else:
                self._assign(environment, component, "attack")