from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Strategy:
      Village:
        1. Feed hungry villagers first (steps_since_meal >= 2), limited by wheat.
        2. Spawn warriors from free farmer pairs while the wheat left after the
           spawn covers the meals needed next step; keep one farmer working.
        3. Healthy warriors that ate recently go to the cave to attack.
        4. Healthy, recently fed farmers also attack when wheat is in surplus,
           always keeping at least one farmer on the farm.
        5. Everyone else stays on the farm.
      Cave:
        1. Warriors that have not eaten for >= 4 steps, or have hp <= 2, go home.
           Farmers go home at >= 3 steps without food or hp <= 2.
        2. Everyone else attacks the Dragon.
    Every component is assigned exactly once per call.
    """

    HUNGRY_THRESHOLD = 2
    WARRIOR_RETURN_THRESHOLD = 4
    FARMER_RETURN_THRESHOLD = 3
    CAVE_MIN_HP = 3
    WARRIOR_SPAWN_COST = 12
    LOW_WHEAT = 10
    FARMER_SURPLUS = 8     # wheat beyond next step's meals needed to send a farmer to attack
    FARMER_ATTACK_MIN_HP = 3

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

        # 2. Spawn warriors from free farmer pairs.
        spawn_ids = set()
        spawned = 0
        while len(free_farmers) - spawned >= 2:
            budget_after = budget - self.WARRIOR_SPAWN_COST
            if budget_after < needing_food:
                break
            farming_after = len(rest_farmers) - (spawned + 2)
            if farming_after == 0 and budget < self.LOW_WHEAT:
                break  # keep wheat income alive when the stock is low
            budget = budget_after
            for c in free_farmers[spawned:spawned + 2]:
                spawn_ids.add(id(c))
            spawned += 2

        # 3. Farmers that may attack: fed, healthy, not spawning.
        # Keep at least one farmer on the farm for wheat income.
        attack_farmer_ids = set()
        candidates = [c for c in free_farmers[spawned:]
                      if c.hp >= self.FARMER_ATTACK_MIN_HP and c.steps_since_meal <= 1]
        surplus = budget - needing_food
        if surplus >= self.FARMER_SURPLUS:
            farmers_on_farm_now = [c for c in rest_farmers if id(c) not in spawn_ids]
            max_sent = max(0, len(farmers_on_farm_now) - 1)
            for c in candidates[:max_sent]:
                attack_farmer_ids.add(id(c))

        # 4. Assign every villager exactly once.
        for c in components:
            cid = id(c)
            if cid in eat_ids:
                environment.assign_group(c, "eat")
            elif cid in spawn_ids:
                environment.assign_group(c, "spawn warrior")
            elif cid in attack_farmer_ids:
                environment.assign_group(c, "cave")
            elif (c.role == "Warrior"
                  and c.hp >= self.CAVE_MIN_HP
                  and c.steps_since_meal <= 1):
                environment.assign_group(c, "cave")
            else:
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.role == "Farmer":
                go_home = (c.steps_since_meal >= self.FARMER_RETURN_THRESHOLD
                           or c.hp <= 2)
            else:
                go_home = (c.steps_since_meal >= self.WARRIOR_RETURN_THRESHOLD
                           or c.hp <= 2)
            if go_home:
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")