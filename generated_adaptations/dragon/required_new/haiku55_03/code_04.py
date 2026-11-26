from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Fast Dragon hunt with warrior rotation and early warrior spawning.

    Village:
      - Hungry villagers eat first (limited by wheat), most hungry first.
      - Warriors that are fed go to the Cave to attack.
      - If wheat allows (after meals), two farmers spawn a new Warrior.
      - Remaining farmers keep farming.

    Cave:
      - Warriors attack while steps_since_meal <= 3 (safe margin).
      - Finishing blow: if the warriors that are not yet starving can kill
        the Dragon this step, all of them attack regardless of hunger.
      - Everyone else returns to the Village to eat.
    """

    WARRIOR_EAT_THRESHOLD = 1     # a hungry warrior in the Village eats
    FARMER_EAT_THRESHOLD = 3      # farmers eat before the 6-step limit
    CAVE_RETURN_THRESHOLD = 4     # warriors in the Cave leave at this hunger
    STARVE_LIMIT = 6              # a villager starves at 6 steps without a meal
    SPAWN_WARRIOR_WHEAT = 12
    DAMAGE_PER_WARRIOR = 3

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        assigned = set()

        def give(c, group):
            if id(c) in assigned:
                return
            environment.assign_group(c, group)
            assigned.add(id(c))

        # 1) Decide who needs food.
        hungry = []
        for c in components:
            threshold = (self.WARRIOR_EAT_THRESHOLD if c.role == "Warrior"
                         else self.FARMER_EAT_THRESHOLD)
            if c.steps_since_meal >= threshold:
                hungry.append(c)
        # Most hungry first, so nobody starves when wheat is scarce.
        hungry.sort(key=lambda c: c.steps_since_meal, reverse=True)

        n_fed = min(len(hungry), max(0, wheat))
        fed = hungry[:n_fed]
        for c in fed:
            give(c, "eat")

        # Hungry villagers who could not be fed keep working on the farm.
        remaining = [c for c in components if id(c) not in assigned]
        wheat_left = wheat - n_fed

        # 2) Spawn a Warrior if wheat allows and two farmers are free.
        free_farmers = [c for c in remaining if c.role == "Farmer"]
        if wheat_left >= self.SPAWN_WARRIOR_WHEAT and len(free_farmers) >= 2:
            for c in free_farmers[:2]:
                give(c, "spawn warrior")

        # 3) Fed-or-healthy warriors head to the Cave; everyone else farms.
        for c in remaining:
            if id(c) in assigned:
                continue
            if c.role == "Warrior" and c.steps_since_meal < self.WARRIOR_EAT_THRESHOLD:
                give(c, "cave")
            else:
                give(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        assigned = set()

        def give(c, group):
            if id(c) in assigned:
                return
            environment.assign_group(c, group)
            assigned.add(id(c))

        # Warriors that can still attack this step without starving.
        capable = [c for c in components
                   if c.role == "Warrior" and c.hp > 0
                   and c.steps_since_meal < self.STARVE_LIMIT - 1]
        potential_damage = len(capable) * self.DAMAGE_PER_WARRIOR
        dragon_hp = environment.dragon.hp
        finishing_blow = len(capable) > 0 and potential_damage >= dragon_hp

        for c in components:
            if c.role == "Warrior" and c.hp > 0:
                if finishing_blow and c in capable:
                    give(c, "attack")
                elif c.steps_since_meal <= self.CAVE_RETURN_THRESHOLD - 1:
                    give(c, "attack")
                else:
                    give(c, "village")
            else:
                give(c, "village")