from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Warrior strike force with scheduled feeding.

    - Warriors do the damage in the Cave (3 dmg per attack).
    - Farmers stay in the Village, farm wheat, and are used to spawn new warriors
      when wheat is plentiful.
    - Villagers are sent to eat once they have gone 3 steps without a meal, which
      keeps everyone well below the 6-step starvation limit, even counting the
      step needed to travel between Cave and Village.
    - Warriors rotate out of the Cave when hungry or badly hurt.
    """

    FEED_THRESHOLD = 3       # eat when steps_since_meal reaches this value
    SPAWN_WHEAT_MIN = 15     # wheat needed before spending farmers on a spawn
    LOW_HP = 2               # warriors at or below this HP retreat to the Village

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        needs_food = []
        others = []

        # 1) Feed anyone who is getting hungry.
        for c in components:
            if c.steps_since_meal >= self.FEED_THRESHOLD:
                needs_food.append(c)
            else:
                others.append(c)

        # Each meal costs 1 wheat; account for it before planning spawns.
        wheat_after_meals = wheat - len(needs_food)

        # 2) Spawn new warriors from idle farmers when wheat allows it.
        spawn_candidates = [c for c in others if c.role == "Farmer"]
        spawning = []
        if wheat_after_meals >= self.SPAWN_WHEAT_MIN and len(spawn_candidates) >= 2:
            spawning = spawn_candidates[:2]

        remaining = [c for c in others if c not in spawning]

        # 3) Dispatch the rest.
        to_cave = []
        to_farm = []
        for c in remaining:
            if c.role == "Warrior" and c.hp > self.LOW_HP and c.steps_since_meal < self.FEED_THRESHOLD:
                to_cave.append(c)
            else:
                to_farm.append(c)

        for c in needs_food:
            environment.assign_group(c, "eat")
        for c in spawning:
            environment.assign_group(c, "spawn warrior")
        for c in to_cave:
            environment.assign_group(c, "cave")
        for c in to_farm:
            environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            # Retreat if hungry, hurt, or a farmer.
            if c.role == "Farmer":
                environment.assign_group(c, "village")
            elif c.steps_since_meal >= self.FEED_THRESHOLD or c.hp <= self.LOW_HP:
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")