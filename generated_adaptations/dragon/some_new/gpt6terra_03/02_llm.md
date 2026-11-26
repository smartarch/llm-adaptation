The strategy builds a small farming base and recruits warriors before launching an attack. Once the force is ready, warriors attack whenever they can; reinforcements continue to be recruited while time permits. Farmers remain in the Village to support feeding and recruitment, with some sent as late reinforcements.

Villagers in the Cave return when their meal counter reaches 4, leaving time to eat in the Village before six consecutive missed meals. Village villagers due for a meal take priority over spawning. This timing cannot guarantee feeding from an already unrecoverable starting state—for example, a villager already in the Cave at counter 5, or insufficient wheat when a meal is due.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.launched = False

    def _update_phase(self, environment, step):
        warriors = list(environment.warriors)
        if (
            len(warriors) >= 6
            or environment.dragon.hp < 100
            or step >= 15
            or any(w.location == "Cave" for w in warriors)
        ):
            self.launched = True

    def assign_in_village(self, components, environment, group_ids, step: int):
        self._update_phase(environment, step)
        villagers = list(components)
        assignments = [None] * len(villagers)

        all_farmers = list(environment.farmers)
        all_warriors = list(environment.warriors)
        wheat = max(0, environment.farm.wheat)

        # Feed villagers who must eat now. If wheat is insufficient, assigning
        # them to eat is still their best chance, although it may not succeed.
        due = sorted(
            (i for i, v in enumerate(villagers) if v.steps_since_meal >= 5),
            key=lambda i: (-villagers[i].steps_since_meal, villagers[i].hp),
        )
        for i in due:
            assignments[i] = "eat"
        wheat = max(0, wheat - len(due))

        # Reserve food for villagers likely to need a meal next step, including
        # cave villagers returning this step.
        next_meals = sum(
            1 for v in villagers if v.steps_since_meal == 4
        ) + sum(
            1
            for v in all_farmers + all_warriors
            if v.location == "Cave" and v.steps_since_meal >= 4
        )
        spending_budget = max(0, wheat - next_meals)

        # Once the attack is underway, refresh older warriors early so they can
        # make a useful trip to the Cave rather than immediately returning.
        if self.launched:
            refresh = sorted(
                (
                    i for i, v in enumerate(villagers)
                    if assignments[i] is None
                    and v.role == "Warrior"
                    and v.steps_since_meal >= 3
                ),
                key=lambda i: (-villagers[i].steps_since_meal, villagers[i].hp),
            )
            for i in refresh:
                if spending_budget < 1:
                    break
                assignments[i] = "eat"
                spending_budget -= 1

        # Recruit while there is enough time for new villagers to contribute.
        # Keep at least one available villager farming when possible.
        if step < 24:
            available = [i for i in range(len(villagers)) if assignments[i] is None]
            available.sort(
                key=lambda i: (
                    villagers[i].role != "Farmer",
                    -villagers[i].steps_since_meal,
                )
            )
            max_pairs = len(available) // 2
            if len(available) >= 3:
                max_pairs = (len(available) - 1) // 2

            farmer_count = len(all_farmers)
            warrior_count = len(all_warriors)
            cursor = 0

            for _ in range(max_pairs):
                if farmer_count < 3 and step < 8:
                    group, cost = "spawn farmer", 10
                elif warrior_count < 12:
                    group, cost = "spawn warrior", 12
                else:
                    break

                if spending_budget < cost:
                    break

                assignments[available[cursor]] = group
                assignments[available[cursor + 1]] = group
                cursor += 2
                spending_budget -= cost

                if group == "spawn farmer":
                    farmer_count += 1
                else:
                    warrior_count += 1

        # Send sufficiently fed warriors to attack. Late in the game, use
        # farmers as reinforcements too, while retaining one Village worker
        # when possible.
        candidates = [
            i for i, v in enumerate(villagers)
            if assignments[i] is None
            and v.steps_since_meal <= 2
            and (
                (self.launched and v.role == "Warrior")
                or step >= 24
            )
        ]
        candidates.sort(
            key=lambda i: (villagers[i].role != "Warrior", villagers[i].steps_since_meal)
        )

        remaining_in_village = len(villagers)
        for i in candidates:
            if remaining_in_village <= 1:
                break
            assignments[i] = "cave"
            remaining_in_village -= 1

        for i, villager in enumerate(villagers):
            environment.assign_group(villager, assignments[i] or "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        self._update_phase(environment, step)

        for villager in components:
            if villager.steps_since_meal >= 4:
                group = "village"
            else:
                group = "attack"
            environment.assign_group(villager, group)
```