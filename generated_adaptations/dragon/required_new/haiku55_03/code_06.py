from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Fast Dragon hunt with warrior rotation and early warrior spawning.

    Village:
      - Hungry villagers eat first (limited by wheat), most hungry first.
      - Warriors that are fed (and not hungry) go to the Cave to attack.
      - If wheat allows (after meals), two farmers spawn a new Warrior.
      - Remaining villagers farm.

    Cave:
      - Warriors attack while steps_since_meal <= 2 (safe margin).
      - Finishing blow: if the warriors that are still safe (steps <= 3) can
        kill the Dragon this step, they all attack.
      - Everyone else (including warriors with steps_since_meal >= 3) returns
        to the Village to eat.
    """

    WARRIOR_EAT_THRESHOLD = 1     # a hungry warrior in the Village eats
    FARMER_EAT_THRESHOLD = 3      # farmers eat before the 6-step limit
    CAVE_ATTACK_MAX_STEPS = 2     # warriors in the Cave attack while steps <= 2
    FINISH_MAX_STEPS = 3          # finishing blow allowed up to this hunger
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
        for c in hungry[:n_fed]:
            give(c, "eat")

        # 2) Spawn a Warrior if wheat allows and two farmers are free.
        remaining = [c for c in components if id(c) not in assigned]
        wheat_left = wheat - n_fed
        free_farmers = [c for c in remaining if c.role == "Farmer"]
        if wheat_left >= self.SPAWN_WARRIOR_WHEAT and len(free_farmers) >= 2:
            for c in free_farmers[:2]:
                give(c, "spawn warrior")

        # 3) Healthy-fed warriors head to the Cave; everyone else farms.
        for c in components:
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

        # Warriors that are still safe enough to attack this step.
        finish_candidates = [c for c in components
                             if c.role == "Warrior" and c.hp > 0
                             and c.steps_since_meal <= self.FINISH_MAX_STEPS]
        potential_damage = len(finish_candidates) * self.DAMAGE_PER_WARRIOR
        finishing_blow = (len(finish_candidates) > 0
                          and potential_damage >= environment.dragon.hp)

        for c in components:
            if c.role == "Warrior" and c.hp > 0:
                if c.steps_since_meal <= self.CAVE_ATTACK_MAX_STEPS:
                    give(c, "attack")
                elif finishing_blow and c in finish_candidates:
                    give(c, "attack")
                else:
                    give(c, "village")
            else:
                give(c, "village")