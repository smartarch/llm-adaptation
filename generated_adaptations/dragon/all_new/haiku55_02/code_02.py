from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Strategy:
    - Warriors are the damage dealers (3 dmg/step); farmers produce wheat
      (5/step) that pays for meals and spawning.
    - Any villager that has not eaten for HUNGER_LIMIT steps is sent to eat
      in the Village, well before the 6-step starvation limit.
    - Fed warriors keep attacking in the Cave; farmers stay on the farm.
    - Extra warriors are spawned from pairs of healthy farmers while wheat
      is available and the warrior count is below MAX_WARRIORS.
    """

    HUNGER_LIMIT = 3       # go eat when steps_since_meal reaches this value
    MAX_WARRIORS = 6       # stop spawning warriors beyond this count
    WARRIOR_COST = 12      # wheat cost of spawning a warrior
    WHEAT_RESERVE = 2      # wheat kept aside for meals

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        comps = list(components)
        wheat = environment.farm.wheat
        dragon_alive = environment.dragon.hp > 0

        hungry = [c for c in comps if c.steps_since_meal >= self.HUNGER_LIMIT]
        fed = [c for c in comps if c.steps_since_meal < self.HUNGER_LIMIT]

        # 1. Hungry villagers eat (each meal costs 1 wheat).
        for c in hungry:
            environment.assign_group(c, "eat")
        wheat_after_meals = wheat - len(hungry)

        # 2. Possibly spawn a new warrior from two fed farmers.
        spawn_candidates = [c for c in fed if c.role == "Farmer"]
        spawned = set()
        num_warriors = len(environment.warriors)
        if (dragon_alive
                and num_warriors < self.MAX_WARRIORS
                and wheat_after_meals - self.WHEAT_RESERVE >= self.WARRIOR_COST
                and len(spawn_candidates) >= 2):
            for c in spawn_candidates[:2]:
                environment.assign_group(c, "spawn warrior")
                spawned.add(id(c))

        # 3. Remaining fed villagers.
        for c in fed:
            if id(c) in spawned:
                continue
            if c.role == "Warrior" and dragon_alive:
                environment.assign_group(c, "cave")
            else:
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.role == "Warrior" and c.steps_since_meal < self.HUNGER_LIMIT:
                # Healthy warriors keep hitting the Dragon every step.
                environment.assign_group(c, "attack")
            else:
                # Hungry warriors and farmers return to eat/farm.
                environment.assign_group(c, "village")