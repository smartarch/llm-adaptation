from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Strategy:
    - Wheat is reserved for meals before any spawning, so no one starves for lack of food.
    - At least 2 farmers always keep farming to sustain wheat income.
    - Early on, spare farmers spawn farmers (cheap economy boost); later they spawn warriors.
    - Warriors cycle: attack in the Cave while steps_since_meal < 3, then eat in the Village
      and return to the Cave. Farmers eat at 4 steps (they never leave the Village).
    """

    WARRIOR_LEAVE_CAVE_AT = 3
    FARMER_EAT_AT = 4
    WARRIOR_COST = 12
    FARMER_COST = 10
    ECONOMY_STEPS = 8
    MAX_FARMERS_FOR_ECONOMY = 6
    MIN_FARMERS_FARMING = 2

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat

        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # 1) Decide who must eat. Warriors need a meal once they are not fresh;
        #    farmers eat at the threshold. If wheat is short, the most hungry eat first.
        candidates = [c for c in warriors if c.steps_since_meal >= 1]
        candidates += [c for c in farmers if c.steps_since_meal >= self.FARMER_EAT_AT]
        candidates.sort(key=lambda c: c.steps_since_meal, reverse=True)

        eaters = candidates[:max(0, wheat)]
        eater_ids = {id(c) for c in eaters}
        for c in eaters:
            environment.assign_group(c, "eat")
        wheat -= len(eaters)

        idle_farmers = [c for c in farmers if id(c) not in eater_ids]
        fresh_warriors = [c for c in warriors if id(c) not in eater_ids]

        # 2) Wheat reserve for upcoming meals.
        reserve = len(warriors) // 2 + 2

        # 3) Spawning, keeping at least MIN_FARMERS_FARMING farmers on the farm.
        spawn_ids = set()
        total_farmers = len(farmers)
        while len(idle_farmers) - len(spawn_ids) >= 2 + self.MIN_FARMERS_FARMING and len(spawn_ids) == 0:
            # Early: boost economy with farmers while the farm is small.
            if step < self.ECONOMY_STEPS and total_farmers < self.MAX_FARMERS_FOR_ECONOMY \
                    and wheat - reserve >= self.FARMER_COST:
                cost, role = self.FARMER_COST, "spawn farmer"
            elif wheat - reserve >= self.WARRIOR_COST:
                cost, role = self.WARRIOR_COST, "spawn warrior"
            else:
                break
            pool = [c for c in idle_farmers if id(c) not in spawn_ids]
            pair = pool[:2]
            for c in pair:
                environment.assign_group(c, role)
                spawn_ids.add(id(c))
            wheat -= cost
            total_farmers += 0  # newborns are added next step

        # Allow additional warrior pairs in the same step if wheat is plentiful.
        while True:
            pool = [c for c in idle_farmers if id(c) not in spawn_ids]
            if len(pool) - 2 < self.MIN_FARMERS_FARMING or wheat - reserve < self.WARRIOR_COST:
                break
            pair = pool[:2]
            for c in pair:
                environment.assign_group(c, "spawn warrior")
                spawn_ids.add(id(c))
            wheat -= self.WARRIOR_COST

        # 4) Fresh warriors go to the Cave to fight.
        for c in fresh_warriors:
            environment.assign_group(c, "cave")

        # 5) Remaining farmers farm wheat.
        for c in idle_farmers:
            if id(c) not in spawn_ids:
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.role == "Warrior" and c.hp > 0 and c.steps_since_meal < self.WARRIOR_LEAVE_CAVE_AT:
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")