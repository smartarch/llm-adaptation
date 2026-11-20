from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Village:
      1. Mandatory meals: villagers with steps_since_meal >= 2 eat (paid first).
      2. Economy: while total farmers < FARMER_TARGET and step <= ECONOMY_STEPS,
         and wheat is not already plentiful, pairs of free farmers spawn farmers (10 wheat).
      3. Army: pairs of free farmers spawn warriors (12 wheat), uncapped.
      4. Warriors not eating/spawning go to the cave; everyone else farms.
    Cave:
      - Farmers return to the village.
      - Warriors attack while steps_since_meal < CAVE_ATTACK_LIMIT; otherwise return to eat.
      - Once the Dragon is dead, everyone waits in the cave.
    """

    EAT_THRESHOLD = 2
    CAVE_ATTACK_LIMIT = 4
    ECONOMY_STEPS = 14
    FARMER_TARGET = 10
    WHEAT_PLENTIFUL = 24  # above this, skip farmer spawns and go straight to warriors
    FARMER_COST = 10
    WARRIOR_COST = 12

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        assigned = {}

        # 1) Mandatory meals (paid first so nobody starves).
        eaters = [c for c in components if c.steps_since_meal >= self.EAT_THRESHOLD]
        for c in eaters:
            assigned[id(c)] = "eat"
        wheat -= len(eaters)

        # Free farmers not eating are candidates for spawning.
        free_farmers = [c for c in components
                        if c.role == "Farmer" and id(c) not in assigned]
        # Farmers never leave the village, so this is the total farmer count.
        total_farmers = sum(1 for c in components if c.role == "Farmer")

        # 2) Economy: grow the farmer population unless wheat is already plentiful.
        if step <= self.ECONOMY_STEPS and wheat < self.WHEAT_PLENTIFUL:
            while (len(free_farmers) >= 2
                   and total_farmers < self.FARMER_TARGET
                   and wheat >= self.FARMER_COST):
                a, b = free_farmers.pop(), free_farmers.pop()
                assigned[id(a)] = "spawn farmer"
                assigned[id(b)] = "spawn farmer"
                wheat -= self.FARMER_COST
                total_farmers += 1

        # 3) Army: warriors with all remaining wheat.
        while len(free_farmers) >= 2 and wheat >= self.WARRIOR_COST:
            a, b = free_farmers.pop(), free_farmers.pop()
            assigned[id(a)] = "spawn warrior"
            assigned[id(b)] = "spawn warrior"
            wheat -= self.WARRIOR_COST

        # 4) Remaining villagers: warriors go to the cave, farmers farm.
        for c in components:
            if id(c) in assigned:
                continue
            if c.role == "Warrior":
                assigned[id(c)] = "cave"
            else:
                assigned[id(c)] = "farm"

        for c in components:
            environment.assign_group(c, assigned[id(c)])

    def assign_in_cave(self, components, environment, group_ids, step: int):
        dragon_alive = environment.dragon.hp > 0
        for c in components:
            if c.role == "Farmer":
                environment.assign_group(c, "village")
            elif c.steps_since_meal >= self.CAVE_ATTACK_LIMIT:
                environment.assign_group(c, "village")
            elif dragon_alive:
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "cave")