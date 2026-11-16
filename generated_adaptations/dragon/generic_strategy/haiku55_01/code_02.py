from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Warrior surge strategy:
      - Farmers stay in the Village, farm wheat, eat on schedule and fund spawns.
      - Warriors are spawned (from pairs of Farmers) whenever wheat allows.
      - Warriors attack the Dragon from the Cave and return to eat before starving.
    """

    EAT_THRESHOLD = 3        # eat in the Village when this many steps have passed without a meal
    CAVE_RETURN_THRESHOLD = 3  # Warriors in the Cave return to eat at this point
    WARRIOR_COST = 12
    FARMER_COST = 10
    MAX_SPAWNS_PER_STEP = 2
    EARLY_FARMER_STEPS = 8   # only spawn extra farmers during the first few steps

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        dragon_alive = environment.dragon.hp > 0
        budget = wheat

        eaters = []
        rest = []
        # 1) Schedule meals: anyone close to starving eats (costs 1 wheat each)
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

        # 2) Spawn warriors from farmer pairs while wheat allows
        spawns = 0
        while (dragon_alive and spawns < self.MAX_SPAWNS_PER_STEP
               and len(free_farmers) >= 2 and budget >= self.WARRIOR_COST):
            spawn_warrior.extend([free_farmers.pop(), free_farmers.pop()])
            budget -= self.WARRIOR_COST
            spawns += 1

        # 3) Early economy: spawn farmers if no warrior was possible
        if (not spawn_warrior and step < self.EARLY_FARMER_STEPS
                and len(free_farmers) >= 2 and budget >= self.FARMER_COST):
            spawn_farmer.extend([free_farmers.pop(), free_farmers.pop()])
            budget -= self.FARMER_COST

        # 4) Warriors that are not needed for eating head to the Cave
        to_cave = []
        if dragon_alive:
            to_cave = list(free_warriors)
            free_warriors = []

        # 5) Everyone else keeps farming (leftover farmers and any held-back warriors)
        farming = free_farmers + free_warriors

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
            # Farmers and starving/near-starving Warriors go home to eat
            if c.role == "Farmer" or c.steps_since_meal >= self.CAVE_RETURN_THRESHOLD:
                environment.assign_group(c, "village")
            else:
                # Healthy Warriors fight
                environment.assign_group(c, "attack")