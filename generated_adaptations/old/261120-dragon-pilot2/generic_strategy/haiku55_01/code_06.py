from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Warrior surge with safe meal scheduling:
      - Warriors are spawned from Farmer pairs whenever wheat allows.
      - Warriors attack in the Cave and return at 3 steps without a meal,
        so they arrive at about 4 steps and eat immediately (no starvation).
      - Farmers stay in the Village, farm, and eat on schedule.
    """

    EAT_THRESHOLD = 3           # Village: eat when this many steps have passed without a meal
    CAVE_RETURN_THRESHOLD = 3   # Cave: Warriors go home at this point (safe margin for travel)
    WARRIOR_COST = 12
    FARMER_COST = 10
    EARLY_FARMER_STEPS = 6      # only consider extra farmers in the first few steps
    EARLY_FARMER_MIN_WHEAT = 20

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        dragon_alive = environment.dragon.hp > 0
        budget = wheat

        eaters = []
        rest = []
        # 1) Meals first: anyone close to starving eats (1 wheat each)
        for c in components:
            if c.steps_since_meal >= self.EAT_THRESHOLD and budget >= 1:
                eaters.append(c)
                budget -= 1
            else:
                rest.append(c)

        free_farmers = [c for c in rest if c.role == "Farmer"]
        free_warriors = [c for c in rest if c.role == "Warrior"]

        spawn_warrior = []
        spawn_farmer = []

        # 2) Warrior surge: spawn as many Warriors as affordable
        if dragon_alive:
            while len(free_farmers) >= 2 and budget >= self.WARRIOR_COST:
                spawn_warrior.extend([free_farmers.pop(), free_farmers.pop()])
                budget -= self.WARRIOR_COST

        # 3) Early economy: a Farmer pair only if no Warrior was possible and wheat is comfortable
        if (not spawn_warrior and step < self.EARLY_FARMER_STEPS
                and len(free_farmers) >= 2 and budget >= self.EARLY_FARMER_MIN_WHEAT):
            spawn_farmer.extend([free_farmers.pop(), free_farmers.pop()])
            budget -= self.FARMER_COST

        # 4) Free Warriors head to the Cave to attack
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