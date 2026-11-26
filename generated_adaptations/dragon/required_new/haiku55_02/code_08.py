from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Strategy:
    - Feed villagers in order of urgency. Anyone with 3+ steps without a meal
      eats in the village if wheat allows; otherwise they farm.
    - Spawn warriors from pairs of non-hungry farmers whenever the wheat left
      over still covers the meals due in the next step. Spawning continues
      until step 26 so new warriors have time to deal damage.
    - Healthy warriors attack in the Cave; everyone else farms.
    - In the Cave, warriors attack until they are hungry (4+ steps without a
      meal) or badly hurt (HP <= 2), then return to the Village.
    """

    HUNGER_THRESHOLD_VILLAGE = 3   # eat in the village at this point
    HUNGER_SOON = 2                # will need a meal next step
    HUNGER_THRESHOLD_CAVE = 4      # return from the cave to eat at this point
    SPAWN_STEP_LIMIT = 26          # late spawns still add some damage
    WARRIOR_SPAWN_COST = 12
    MIN_WARRIOR_HP_FOR_CAVE = 3
    MIN_HP_IN_CAVE = 2             # return to village at or below this HP
    WHEAT_MARGIN = 0               # reserve only what the next meals need

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        all_villagers = list(environment.warriors) + list(environment.farmers)

        # 1) Feed the most urgent villagers first, as long as wheat allows.
        fed = []
        unfed = []
        for c in sorted(components, key=lambda v: -v.steps_since_meal):
            if c.steps_since_meal >= self.HUNGER_THRESHOLD_VILLAGE and wheat >= 1:
                environment.assign_group(c, "eat")
                wheat -= 1
                fed.append(c)
            else:
                unfed.append(c)

        # 2) Meals due next step from villagers not fed this step.
        needs_next = sum(1 for v in all_villagers if v.steps_since_meal >= self.HUNGER_SOON)
        needs_next = max(0, needs_next - len(fed))

        # 3) Spawn warriors from pairs of non-hungry farmers while wheat allows.
        spawned = []
        if step <= self.SPAWN_STEP_LIMIT:
            spawn_candidates = [
                c for c in unfed
                if c.role == "Farmer" and c.steps_since_meal < self.HUNGER_THRESHOLD_VILLAGE
            ]
            while (len(spawn_candidates) - len(spawned) >= 2
                   and wheat - self.WARRIOR_SPAWN_COST >= needs_next + self.WHEAT_MARGIN):
                pair = [c for c in spawn_candidates if c not in spawned][:2]
                for c in pair:
                    environment.assign_group(c, "spawn warrior")
                    spawned.append(c)
                wheat -= self.WARRIOR_SPAWN_COST

        # 4) Healthy warriors fight; everyone else farms.
        for c in unfed:
            if c in spawned:
                continue
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