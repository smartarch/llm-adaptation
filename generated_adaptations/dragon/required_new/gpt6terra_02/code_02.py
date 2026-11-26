from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.launched = False

    def assign_in_village(self, components, environment, group_ids, step: int):
        villagers = list(components)
        warriors = list(environment.warriors)
        farmers = list(environment.farmers)
        population = len(warriors) + len(farmers)
        wheat = max(0, environment.farm.wheat)

        # Once fighting starts, continue reinforcing instead of staging again.
        if (
            len(warriors) >= 4
            or step >= 10
            or environment.dragon.hp < 100
            or any(w.location == "Cave" for w in warriors)
            or any(f.location == "Cave" for f in farmers)
        ):
            self.launched = True

        assignments = {}

        def assign(villager, group):
            assignments[id(villager)] = group

        def unassigned():
            return [v for v in villagers if id(v) not in assignments]

        # Feed the most overdue villagers first. Warriors eat early after
        # launch so that they can spend more consecutive steps attacking.
        def needs_food(v):
            if v.steps_since_meal >= 4:
                return True
            if self.launched and v.role == "Warrior":
                return v.steps_since_meal >= 2
            if step >= 24 and v.role == "Farmer":
                return v.steps_since_meal >= 2
            return False

        hungry = sorted(
            (v for v in villagers if needs_food(v)),
            key=lambda v: v.steps_since_meal,
            reverse=True,
        )
        for villager in hungry:
            if wheat >= 1:
                assign(villager, "eat")
                wheat -= 1

        # Keep a producer farming when reserves are low.
        available = unassigned()
        if wheat < population + 12 and available:
            producer = max(
                available,
                key=lambda v: (v.role == "Farmer", v.hp),
            )
            assign(producer, "farm")

        # Spawn at most one villager per step. Reserve one meal per living
        # villager, including those currently in the cave.
        available = unassigned()
        spawn_role = "farmer" if not farmers else "warrior"
        cost = 10 if spawn_role == "farmer" else 12
        if step < 24 and len(available) >= 2 and wheat >= cost + population:
            # Prefer using warriors as parents, leaving farmers to produce.
            parents = sorted(
                available,
                key=lambda v: (v.role != "Warrior", v.hp),
            )[:2]
            for parent in parents:
                assign(parent, "spawn " + spawn_role)
            wheat -= cost

        for villager in unassigned():
            fresh = villager.steps_since_meal <= 1
            if self.launched and fresh and villager.role == "Warrior":
                assign(villager, "cave")
            elif step >= 24 and fresh and villager.role == "Farmer":
                assign(villager, "cave")
            else:
                assign(villager, "farm")

        # Explicitly reassign every villager, including those continuing
        # their previous action.
        for villager in villagers:
            environment.assign_group(villager, assignments[id(villager)])

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for villager in components:
            # Returning takes a step; on arrival the villager can eat before
            # reaching six consecutive steps without a meal.
            if villager.steps_since_meal >= 4:
                group = "village"
            else:
                group = "attack"
            environment.assign_group(villager, group)