from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Fast-kill strategy: use farmers as the spawn pool every step, keep
    warriors attacking, and never let anyone starve.

    - Hungry villagers eat in the Village, most hungry first, within wheat stock.
    - Idle farmers form spawn pairs (12 wheat per warrior) while wheat still
      covers the meals due next step and the warriors waiting in the Cave.
    - Healthy warriors attack from the Cave; they leave when hungry or hurt.
    - Farmers never enter the Cave.
    """

    EAT_IN_VILLAGE = 2        # eat in the Village once this hungry
    CAVE_MAX_HUNGER = 4       # warriors leave the Cave at this hunger level
    LOW_HP = 2                # warriors at or below this HP retreat
    WARRIOR_COST = 12

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        assignment = {}

        # 1) Meals, most hungry first, limited by available wheat.
        hungry = sorted(
            [c for c in components if c.steps_since_meal >= self.EAT_IN_VILLAGE],
            key=lambda c: -c.steps_since_meal,
        )
        budget = wheat
        for c in hungry:
            if budget >= 1:
                assignment[id(c)] = "eat"
                budget -= 1
            else:
                assignment[id(c)] = "farm"

        # Meals that will be due next step: villagers in the Village nearly
        # hungry, plus warriors in the Cave that will return to eat.
        due_next = sum(
            1 for c in components
            if id(c) not in assignment or assignment[id(c)] == "eat"
            if c.steps_since_meal + 1 >= self.EAT_IN_VILLAGE
        )
        due_next += len(environment.warriors) - sum(
            1 for w in environment.warriors if w.location == "Village"
        )
        due_next += len(environment.farmers) - sum(
            1 for f in environment.farmers if f.location == "Village"
        )

        # 2) Spawn pool: idle farmers only. Warriors keep attacking.
        free_farmers = [
            c for c in components
            if id(c) not in assignment and c.role == "Farmer"
        ]
        used = 0
        while len(free_farmers) - used >= 2:
            if budget - self.WARRIOR_COST < due_next:
                break
            for c in free_farmers[used:used + 2]:
                assignment[id(c)] = "spawn warrior"
            used += 2
            budget -= self.WARRIOR_COST

        # 3) Remaining villagers: healthy warriors attack, everyone else farms.
        for c in components:
            if id(c) in assignment:
                continue
            if (
                c.role == "Warrior"
                and c.hp > self.LOW_HP
                and c.steps_since_meal < self.CAVE_MAX_HUNGER
            ):
                assignment[id(c)] = "cave"
            else:
                assignment[id(c)] = "farm"

        for c in components:
            environment.assign_group(c, assignment.get(id(c), "farm"))

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.role == "Farmer":
                environment.assign_group(c, "village")
            elif c.steps_since_meal >= self.CAVE_MAX_HUNGER or c.hp <= self.LOW_HP:
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")