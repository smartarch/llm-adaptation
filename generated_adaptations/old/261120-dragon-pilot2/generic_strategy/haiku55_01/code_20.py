from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Warrior surge with a role-specific meal schedule (single structural change):
      - Farmers eat at 4 steps without a meal (they never travel, so they can wait longer).
      - Warriors eat at 3 steps without a meal, paid from a running wheat budget.
      - Warrior spawns from Farmer pairs, up to three spawns per step.
      - Early Farmer spawns in the first 16 steps when no Warrior is affordable.
      - Warriors attack in the Cave and return at 3 steps without a meal.
      - Farmers stay in the Village to farm.
    """

    WARRIOR_EAT_THRESHOLD = 3
    FARMER_EAT_THRESHOLD = 4    # changed: Farmers eat less often, saving wheat
    CAVE_RETURN_THRESHOLD = 3
    WARRIOR_COST = 12
    FARMER_COST = 10
    MAX_SPAWNS_PER_STEP = 3
    EARLY_FARMER_STEPS = 16

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _eat_threshold(self, c):
        if c.role == "Farmer":
            return self.FARMER_EAT_THRESHOLD
        return self.WARRIOR_EAT_THRESHOLD

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        dragon_alive = environment.dragon.hp > 0
        budget = wheat

        # 1) Meals first: anyone at their role's meal threshold eats (1 wheat each)
        eaters = []
        rest = []
        for c in components:
            if c.steps_since_meal >= self._eat_threshold(c) and budget >= 1:
                eaters.append(c)
                budget -= 1
            else:
                rest.append(c)

        free_farmers = [c for c in rest if c.role == "Farmer"]
        free_warriors = [c for c in rest if c.role == "Warrior"]

        spawn_warrior = []
        spawn_farmer = []

        # 2) Warrior surge, capped at MAX_SPAWNS_PER_STEP spawns per step
        spawns = 0
        if dragon_alive:
            while (spawns < self.MAX_SPAWNS_PER_STEP
                   and len(free_farmers) >= 2 and budget >= self.WARRIOR_COST):
                spawn_warrior.extend([free_farmers.pop(), free_farmers.pop()])
                budget -= self.WARRIOR_COST
                spawns += 1

        # 3) Early economy: one Farmer pair if no Warrior was spawned this step
        if (not spawn_warrior and step < self.EARLY_FARMER_STEPS
                and len(free_farmers) >= 2 and budget >= self.FARMER_COST):
            spawn_farmer.extend([free_farmers.pop(), free_farmers.pop()])
            budget -= self.FARMER_COST

        # 4) Free Warriors head to the Cave; everyone else farms
        to_cave = list(free_warriors) if dragon_alive else []
        farming = free_farmers + ([] if dragon_alive else free_warriors)

        for c in eaters:
            environment.assign_group(c, "eat")
        for c in spawn_warrior:
            environment.assign_group(c, "spawn warrior")
        for c in spawn_farmer:
            environment.assign_group(c, "spawn farmer")
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