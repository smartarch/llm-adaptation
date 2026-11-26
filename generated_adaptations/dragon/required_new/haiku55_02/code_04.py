from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Strategy:
    - Spawn warriors as early and as often as wheat allows (pairs of farmers
      go to "spawn warrior"), since warriors are the main source of damage.
    - Healthy warriors fight in the Cave every step; farmers stay on the farm
      to keep producing wheat.
    - Villagers are sent to eat when they have gone 3+ steps without a meal in
      the Village. Warriors in the Cave rotate out only at 4+ steps without a
      meal or when nearly dead, keeping them in the fight longer.
    """

    HUNGER_THRESHOLD_VILLAGE = 3   # eat in the village at this point
    HUNGER_THRESHOLD_CAVE = 4      # return from the cave to eat at this point
    SPAWN_STEP_LIMIT = 24          # warriors spawned later barely contribute
    MEAL_RESERVE = 2               # wheat kept aside for meals
    WARRIOR_SPAWN_COST = 12
    MIN_WARRIOR_HP_FOR_CAVE = 3
    MIN_HP_IN_CAVE = 2             # return to village at or below this HP

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat

        # 1) Hungry villagers eat now (each meal costs 1 wheat).
        hungry = [c for c in components if c.steps_since_meal >= self.HUNGER_THRESHOLD_VILLAGE]
        for c in hungry:
            environment.assign_group(c, "eat")
            wheat -= 1
        ready = [c for c in components if c not in hungry]

        # 2) Spawn warriors from farmer pairs while wheat allows.
        farmers = [c for c in ready if c.role == "Farmer"]
        spawned = set()
        if step <= self.SPAWN_STEP_LIMIT:
            while (len(farmers) - len(spawned) >= 2
                   and wheat >= self.WARRIOR_SPAWN_COST + self.MEAL_RESERVE):
                pair = [c for c in farmers if c not in spawned][:2]
                for c in pair:
                    environment.assign_group(c, "spawn warrior")
                    spawned.add(c)
                wheat -= self.WARRIOR_SPAWN_COST
        ready = [c for c in ready if c not in spawned]

        # 3) Healthy warriors go fight; everyone else farms.
        for c in ready:
            if c.role == "Warrior" and c.hp >= self.MIN_WARRIOR_HP_FOR_CAVE:
                environment.assign_group(c, "cave")
            else:
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if (c.steps_since_meal >= self.HUNGER_THRESHOLD_CAVE
                    or c.hp <= self.MIN_HP_IN_CAVE):
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")