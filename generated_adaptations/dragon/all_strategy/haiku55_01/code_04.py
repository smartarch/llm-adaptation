from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Strategy:
      - Meals first: warriors eat as soon as they are back in the Village
        (steps_since_meal >= 1), farmers at >= 2, and anyone at >= 4 is fed first.
      - Warriors are dispatched to the Cave one per step, and only right after
        eating (steps_since_meal == 0), which staggers their attacks.
      - In the Cave, warriors attack while steps_since_meal <= 4. A hungry warrior
        (>= 3 steps) returns only if another warrior stays behind to keep the
        Dragon under attack; warriors at >= 5 steps always return.
      - Spawning uses only wheat left after meals (plus a small margin).
        Farmers are spawned early while there are few of them; Warriors otherwise.
      - All other villagers farm in the Village.
    """

    FARMER_EAT_THRESHOLD = 2
    WARRIOR_EAT_THRESHOLD = 1
    CRITICAL_HUNGER = 4       # must eat in Village now
    CAVE_RETURN = 3           # hungry enough to go back for food
    CAVE_CRITICAL = 5         # must leave the Cave immediately
    CAVE_ATTACK_MAX = 4       # attack while not too hungry
    WARRIOR_COST = 12
    FARMER_COST = 10
    MARGIN = 2
    TARGET_FARMERS = 4

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        assigned = set()

        # 1) Meals first, most-starved first.
        def needs_meal(c):
            if c.steps_since_meal >= self.CRITICAL_HUNGER:
                return True
            if c.role == "Warrior":
                return c.steps_since_meal >= self.WARRIOR_EAT_THRESHOLD
            return c.steps_since_meal >= self.FARMER_EAT_THRESHOLD

        hungry = sorted(
            [c for c in components if needs_meal(c)],
            key=lambda c: c.steps_since_meal,
            reverse=True,
        )
        for c in hungry:
            if wheat >= 1:
                environment.assign_group(c, "eat")
                assigned.add(id(c))
                wheat -= 1

        remaining = [c for c in components if id(c) not in assigned]

        # 2) Dispatch at most one fresh Warrior (just ate) to the Cave per step.
        dispatched = False
        for c in remaining:
            if c.role == "Warrior" and c.steps_since_meal == 0 and not dispatched:
                environment.assign_group(c, "cave")
                assigned.add(id(c))
                dispatched = True

        remaining = [c for c in components if id(c) not in assigned]

        # 3) Spawning, funded only by wheat left after meals.
        farmers_total = sum(1 for c in components if c.role == "Farmer")
        spawn_candidates = [
            c for c in remaining if c.role == "Farmer" and c.steps_since_meal < self.FARMER_EAT_THRESHOLD
        ]
        spare = wheat - self.MARGIN
        if len(spawn_candidates) >= 2:
            pair = spawn_candidates[:2]
            if farmers_total < self.TARGET_FARMERS and spare >= self.FARMER_COST:
                group = "spawn farmer"
                spare -= self.FARMER_COST
                for c in pair:
                    environment.assign_group(c, group)
                    assigned.add(id(c))
            elif spare >= self.WARRIOR_COST:
                group = "spawn warrior"
                spare -= self.WARRIOR_COST
                for c in pair:
                    environment.assign_group(c, group)
                    assigned.add(id(c))
            elif spare >= self.FARMER_COST:
                group = "spawn farmer"
                spare -= self.FARMER_COST
                for c in pair:
                    environment.assign_group(c, group)
                    assigned.add(id(c))

        # 4) Everyone else stays in the Village and farms (or goes to Cave if already chosen).
        for c in components:
            if id(c) in assigned:
                continue
            environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role != "Warrior"]

        returning = set()
        # Most hungry first; keep at least one warrior attacking unless critical.
        for c in sorted(warriors, key=lambda c: c.steps_since_meal, reverse=True):
            if c.steps_since_meal >= self.CAVE_CRITICAL:
                returning.add(id(c))
            elif c.steps_since_meal >= self.CAVE_RETURN:
                staying = len(warriors) - len(returning) - 1
                if staying >= 1:
                    returning.add(id(c))
                elif len(warriors) == 1:
                    returning.add(id(c))

        for c in farmers:
            environment.assign_group(c, "village")

        for c in warriors:
            if id(c) in returning:
                environment.assign_group(c, "village")
            elif c.steps_since_meal <= self.CAVE_ATTACK_MAX:
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "cave")