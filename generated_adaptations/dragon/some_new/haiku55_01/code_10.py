from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Strategy:
      Village:
        1. Feed hungry villagers first (steps_since_meal >= 2), limited by wheat.
        2. Spawn warriors from free farmer pairs whenever the wheat after the
           spawn, plus the wheat income of farmers still farming, covers the
           meals needed next step.
        3. Healthy warriors that ate recently go to the cave to attack.
        4. Everyone else stays on the farm.
      Cave:
        1. Villagers that have not eaten for >= 3 steps, or have hp <= 1, go home.
        2. Everyone else attacks the Dragon.
    Every component is assigned exactly once per call.
    """

    HUNGRY_THRESHOLD = 2
    RETURN_THRESHOLD = 3
    CAVE_MIN_HP = 2
    WARRIOR_SPAWN_COST = 12
    FARM_INCOME = 5  # wheat produced per farmer per step while farming

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat

        # 1. Feed the hungriest villagers first, limited by wheat.
        hungry = [c for c in components if c.steps_since_meal >= self.HUNGRY_THRESHOLD]
        hungry.sort(key=lambda c: -c.steps_since_meal)
        eat = hungry[:max(0, wheat)]
        eat_ids = {id(c) for c in eat}
        budget = wheat - len(eat)

        rest = [c for c in components if id(c) not in eat_ids]
        rest_farmers = [c for c in rest if c.role == "Farmer"]
        free_farmers = [c for c in rest_farmers if c.steps_since_meal < self.HUNGRY_THRESHOLD]

        # Villagers that will need food next step.
        needing_food = sum(1 for c in rest if c.steps_since_meal >= 1)

        # 2. Spawn warriors from free farmer pairs while wheat and income cover needs.
        spawn_ids = set()
        spawned_farmers = 0
        while len(free_farmers) - spawned_farmers >= 2:
            farming_after = len(rest_farmers) - (spawned_farmers + 2)
            budget_after = budget - self.WARRIOR_SPAWN_COST
            if budget_after < 0:
                break
            if budget_after + self.FARM_INCOME * farming_after < needing_food:
                break
            if farming_after == 0 and budget_after < needing_food:
                break
            budget = budget_after
            for c in free_farmers[spawned_farmers:spawned_farmers + 2]:
                spawn_ids.add(id(c))
            spawned_farmers += 2

        # 3/4. Assign every villager exactly once.
        for c in components:
            cid = id(c)
            if cid in eat_ids:
                environment.assign_group(c, "eat")
            elif cid in spawn_ids:
                environment.assign_group(c, "spawn warrior")
            elif (c.role == "Warrior"
                  and c.hp >= self.CAVE_MIN_HP
                  and c.steps_since_meal <= 1):
                environment.assign_group(c, "cave")
            else:
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.steps_since_meal >= self.RETURN_THRESHOLD or c.hp <= 1:
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")