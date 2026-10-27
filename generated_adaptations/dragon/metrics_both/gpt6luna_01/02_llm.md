The strategy keeps farmers in the Village, feeding them before they reach the starvation limit and using available pairs to spawn two Farmers and two Warriors. Warriors eat in the Village when needed, then travel to the Cave. In the Cave, each newly arrived Warrior is assigned to attack at least once; later meals are staggered so some Warriors can keep attacking while others travel back to eat. Every component is explicitly assigned a group on each call.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._spawned = {"spawn farmer": 0, "spawn warrior": 0}
        self._ranks = {}
        self._next_rank = 0
        self._cave_entry_pending = set()

    def _rank(self, component):
        key = id(component)
        if key not in self._ranks:
            self._ranks[key] = self._next_rank
            self._next_rank += 1
        return self._ranks[key]

    @staticmethod
    def _role(component):
        return str(component.role).lower()

    @staticmethod
    def _assign(environment, component, group_id):
        environment.assign_group(component, group_id)

    def assign_in_village(self, components, environment, group_ids, step: int):
        farmers = []
        for component in components:
            if self._role(component) == "warrior":
                self._rank(component)
            else:
                farmers.append(component)

        assigned = set()
        wheat = max(0, environment.farm.wheat)

        # Eat before the sixth consecutive step without a meal. Warriors eat
        # earlier so they do not depart for the Cave hungry.
        meal_reserve = 0
        for component in components:
            hunger = component.steps_since_meal
            role = self._role(component)
            must_eat = (
                (role == "warrior" and hunger >= 3)
                or (role != "warrior" and hunger >= 5)
            )
            if must_eat:
                self._assign(environment, component, "eat")
                assigned.add(id(component))
                meal_reserve += 1

        # Hold a meal's worth of wheat for farmers who will need to eat soon.
        meal_reserve += sum(
            1 for farmer in farmers
            if id(farmer) not in assigned and farmer.steps_since_meal >= 4
        )
        available_wheat = max(0, wheat - meal_reserve)

        eligible_farmers = [
            farmer for farmer in farmers if id(farmer) not in assigned
        ]
        eligible_farmers.sort(key=lambda c: c.steps_since_meal)

        # Spawn up to two of each type. Use farmer pairs, and only commit a
        # spawn when the wheat cost and current meal reserve are affordable.
        spawn_groups = {"spawn farmer": [], "spawn warrior": []}
        while len(eligible_farmers) >= 2:
            outstanding = [
                name for name in ("spawn warrior", "spawn farmer")
                if self._spawned[name] < 2
            ]
            if not outstanding:
                break

            # Favor the type with fewer completed spawns; favor warriors on ties.
            name = min(
                outstanding,
                key=lambda n: (
                    self._spawned[n],
                    0 if n == "spawn warrior" else 1,
                ),
            )
            cost = 12 if name == "spawn warrior" else 10
            if available_wheat < cost:
                break

            pair = eligible_farmers[:2]
            eligible_farmers = eligible_farmers[2:]
            for farmer in pair:
                self._assign(environment, farmer, name)
                assigned.add(id(farmer))
                spawn_groups[name].append(farmer)

            available_wheat -= cost
            self._spawned[name] += 1

        for name, group in spawn_groups.items():
            if group:
                # The group assignment itself is made per component above;
                # the group contains the required pair(s) for spawning.
                pass

        # Farmers not eating or spawning work the farm. Warriors in the Village
        # travel to the Cave only when they have eaten recently enough.
        for component in components:
            if id(component) in assigned:
                continue

            if self._role(component) == "warrior":
                self._assign(environment, component, "cave")
                self._cave_entry_pending.add(id(component))
            else:
                self._assign(environment, component, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for component in components:
            key = id(component)

            if self._role(component) != "warrior":
                self._assign(environment, component, "village")
                continue

            rank = self._rank(component)

            # Ensure each Warrior attacks at least once after arriving. After
            # that, stagger returns for meals across the Warrior population.
            if key in self._cave_entry_pending:
                self._cave_entry_pending.discard(key)
                self._assign(environment, component, "attack")
                continue

            return_threshold = 3 if rank % 2 == 0 else 4
            if component.steps_since_meal >= return_threshold:
                self._assign(environment, component, "village")
            else:
                self._assign(environment, component, "attack")
```