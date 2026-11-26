from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Strategy:
      Village:
        1. Feed hungry villagers first (steps_since_meal >= 2), limited by wheat.
        2. Spawn warriors from free farmer pairs while the projected wheat
           (stock after spawn + income from farmers and warriors still farming)
           covers the meals needed next step. If no warriors exist, spawn as
           soon as the stock allows.
        3. Early game: spare free farmer pairs spawn new farmers (income growth)
           while the farmer count is below a target and wheat covers next
           step's meals.
        4. Healthy warriors that ate recently go to the cave to attack.
        5. Everyone else (including farmers) stays on the farm.
      Cave:
        1. Warriors that have not eaten for >= 4 steps, or have hp <= 2, go home.
        2. Everyone else attacks the Dragon.
    Every component is assigned exactly once per call.
    """

    HUNGRY_THRESHOLD = 2
    RETURN_THRESHOLD = 4
    CAVE_MIN_HP = 3
    WARRIOR_SPAWN_COST = 12
    FARMER_SPAWN_COST = 10
    FARMER_INCOME = 5
    WARRIOR_INCOME = 2
    EARLY_STEPS = 8          # economy growth only in the early game
    TARGET_FARMERS = 6       # stop growing the farmer count at this size

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat

        # 1. Feed the hungriest villagers first, limited by wheat.
        hungry = [c for c in components if c.steps_since_meal >= self.HUNGRY_THRESHOLD]
        hungry.sort(key=lambda c: -c.steps_since_meal)
        eat = hungry[:max(0, wheat)]
        eat_ids = {id(c) for c in eat}
        budget = wheat - len(eat)

        rest = [c for c in components if id(c) not in eat_ids]
        rest_farmers = [c for c in rest if c.role == "Farmer"]
        free_farmers = [c for c in rest_farmers if c.steps_since_meal < self.HUNGRY_THRESHOLD]
        has_warrior = any(c.role == "Warrior" for c in components)
        all_farmers = [c for c in components if c.role == "Farmer"]

        # Villagers that will need food next step.
        needing_food = sum(1 for c in rest if c.steps_since_meal >= 1)

        spawn_warrior_ids = set()
        spawn_farmer_ids = set()
        used = 0  # index into free_farmers of the next unused farmer

        # 2. Warrior spawns from free farmer pairs using projected income.
        while len(free_farmers) - used >= 2:
            budget_after = budget - self.WARRIOR_SPAWN_COST
            if budget_after < 0:
                break
            pair = free_farmers[used:used + 2]
            pair_ids = {id(c) for c in pair}
            farmers_after = [c for c in rest_farmers
                             if id(c) not in spawn_warrior_ids
                             and id(c) not in pair_ids]
            warriors_farming = [c for c in rest
                                if c.role == "Warrior"
                                and id(c) not in spawn_warrior_ids]
            income = (self.FARMER_INCOME * len(farmers_after)
                      + self.WARRIOR_INCOME * len(warriors_farming))
            if has_warrior and budget_after + income < needing_food:
                break

            budget = budget_after
            spawn_warrior_ids |= pair_ids
            used += 2
            has_warrior = True

        # 3. Early-game farmer growth with the remaining free farmers.
        farmer_count = len(all_farmers)
        if step <= self.EARLY_STEPS:
            while (len(free_farmers) - used >= 2
                   and farmer_count < self.TARGET_FARMERS):
                budget_after = budget - self.FARMER_SPAWN_COST
                if budget_after < needing_food:
                    break
                pair = free_farmers[used:used + 2]
                budget = budget_after
                spawn_farmer_ids |= {id(c) for c in pair}
                used += 2
                farmer_count += 2

        # 4/5. Assign every villager exactly once.
        for c in components:
            cid = id(c)
            if cid in eat_ids:
                environment.assign_group(c, "eat")
            elif cid in spawn_warrior_ids:
                environment.assign_group(c, "spawn warrior")
            elif cid in spawn_farmer_ids:
                environment.assign_group(c, "spawn farmer")
            elif (c.role == "Warrior"
                  and c.hp >= self.CAVE_MIN_HP
                  and c.steps_since_meal <= 1):
                environment.assign_group(c, "cave")
            else:
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.steps_since_meal >= self.RETURN_THRESHOLD or c.hp <= 2:
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")