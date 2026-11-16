from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Warrior surge (baseline restored):
      - Villagers eat at 3 steps without a meal, paid from a running wheat budget.
      - Every affordable pair of free Farmers spawns a Warrior after meals are paid.
      - Warriors attack in the Cave and return at 3 steps without a meal.
      - Farmers stay in the Village to farm.
    """

    EAT_THRESHOLD = 3           # Village: eat when this many steps have passed without a meal
    CAVE_RETURN_THRESHOLD = 3   # Cave: Warriors go home at this point
    WARRIOR_COST = 12

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        dragon_alive = environment.dragon.hp > 0
        budget = wheat

        # 1) Meals first: pay for every villager that is due, while wheat lasts
        eaters = []
        rest = []
        for c in components:
            if c.steps_since_meal >= self.EAT_THRESHOLD and budget >= 1:
                eaters.append(c)
                budget -= 1
            else:
                rest.append(c)

        free_farmers = [c for c in rest if c.role == "Farmer"]
        free_warriors = [c for c in rest if c.role == "Warrior"]

        # 2) Warrior surge: spawn from every affordable pair of free Farmers
        spawn_warrior = []
        if dragon_alive:
            while len(free_farmers) >= 2 and budget >= self.WARRIOR_COST:
                spawn_warrior.extend([free_farmers.pop(), free_farmers.pop()])
                budget -= self.WARRIOR_COST

        # 3) Free Warriors head to the Cave; everyone else farms
        to_cave = list(free_warriors) if dragon_alive else []
        farming = free_farmers + ([] if dragon_alive else free_warriors)

        for c in eaters:
            environment.assign_group(c, "eat")
        for c in spawn_warrior:
            environment.assign_group(c, "spawn warrior")
        for c in to_cave:
            environment.assign_group(c, "cave")
        for c in farming:
            environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            # Farmers go home to farm; Warriors go home when a meal is due
            if c.role == "Farmer" or c.steps_since_meal >= self.CAVE_RETURN_THRESHOLD:
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")