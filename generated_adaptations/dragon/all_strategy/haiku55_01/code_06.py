from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Strategy:
      - Meals first: warriors eat at >= 2 steps since last meal, farmers at >= 3,
        and anyone at >= 4 is fed first. Eating is funded before spawning.
      - Every fed warrior in the Village is sent to the Cave to attack, so the
        Dragon is hit as often as possible and the warriors do not idle.
      - In the Cave, warriors attack by default. A warrior returns for food at
        >= 3 steps since its last meal. If that would leave no attacker in the
        Cave, it stays, unless it has reached the critical level (>= 5).
      - Spawning uses wheat left after meals (reserve = one wheat per villager).
        Warriors are preferred; farmers are spawned only while there are few.
      - Remaining farmers farm in the Village.
    """

    WARRIOR_EAT_THRESHOLD = 2
    FARMER_EAT_THRESHOLD = 3
    CRITICAL_HUNGER = 4
    CAVE_RETURN = 3
    CAVE_CRITICAL = 5
    WARRIOR_COST = 12
    FARMER_COST = 10
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

        # 2) Every fed warrior goes to the Cave to attack.
        for c in remaining:
            if c.role == "Warrior":
                environment.assign_group(c, "cave")
                assigned.add(id(c))

        remaining = [c for c in components if id(c) not in assigned]

        # 3) Spawning, funded by wheat left after meals (reserve = one per villager).
        reserve = len(components)
        spare = wheat - reserve
        farmers_total = sum(1 for c in components if c.role == "Farmer")
        spawn_candidates = [
            c for c in remaining
            if c.role == "Farmer" and c.steps_since_meal < self.FARMER_EAT_THRESHOLD
        ]
        if len(spawn_candidates) >= 2:
            pair = spawn_candidates[:2]
            group = None
            if spare >= self.WARRIOR_COST:
                group = "spawn warrior"
                spare -= self.WARRIOR_COST
            elif farmers_total < self.TARGET_FARMERS and spare >= self.FARMER_COST:
                group = "spawn farmer"
                spare -= self.FARMER_COST
            if group is not None:
                for c in pair:
                    environment.assign_group(c, group)
                    assigned.add(id(c))

        # 4) Everyone else farms in the Village.
        for c in components:
            if id(c) not in assigned:
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role != "Warrior"]

        for c in farmers:
            environment.assign_group(c, "village")

        returning = set()
        # Most hungry first. Critical warriors always leave; others leave only
        # if another warrior remains to keep attacking.
        for c in sorted(warriors, key=lambda w: w.steps_since_meal, reverse=True):
            if c.steps_since_meal >= self.CAVE_CRITICAL:
                returning.add(id(c))
            elif c.steps_since_meal >= self.CAVE_RETURN:
                attackers_left = len(warriors) - len(returning) - 1
                if attackers_left >= 1:
                    returning.add(id(c))

        for c in warriors:
            if id(c) in returning:
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")