from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    # Farmers must eat before they reach 6 steps without food.
    FARMER_EAT_THRESHOLD = 4
    # Warriors eat in the Village once their meal clock reaches this value.
    WARRIOR_EAT_THRESHOLD = 3
    # Warriors in the Cave walk home once their meal clock reaches this value.
    CAVE_RETURN_THRESHOLD = 4
    # Target population.
    TARGET_FARMERS = 5
    TARGET_WARRIORS = 12
    FARMER_COST = 10
    WARRIOR_COST = 12

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Warriors that stay in the Cave to attack (they are not in the Village
        # component list next step, so they must be counted here).
        self._cave_attackers = 0

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # 1. Collect everyone who needs a meal now.
        wants_food = []
        for c in components:
            if c.role == "Farmer":
                needs = c.steps_since_meal >= self.FARMER_EAT_THRESHOLD
            else:
                needs = c.steps_since_meal >= self.WARRIOR_EAT_THRESHOLD
            if needs:
                wants_food.append(c)

        # Feed the most urgent first, never more villagers than the wheat stock allows.
        wants_food.sort(key=lambda c: c.steps_since_meal, reverse=True)
        eaters = wants_food[:max(0, wheat)]
        eater_ids = {id(c) for c in eaters}
        budget = wheat - len(eaters)

        non_eaters = [c for c in components if id(c) not in eater_ids]
        idle_farmers = [c for c in non_eaters if c.role == "Farmer"]

        # 2. Plan spawns. Each spawn group takes pairs of idle farmers.
        #    Farmers and warriors can be spawned in the same step.
        total_farmers = len(farmers)
        total_warriors = len(warriors) + self._cave_attackers

        spawn_plan = {}  # id(component) -> group name
        pool = list(idle_farmers)

        farmer_deficit = max(0, self.TARGET_FARMERS - total_farmers)
        n_farmer_pairs = min(len(pool) // 2, budget // self.FARMER_COST, farmer_deficit)
        for c in pool[: 2 * n_farmer_pairs]:
            spawn_plan[id(c)] = "spawn farmer"
        pool = pool[2 * n_farmer_pairs:]
        budget -= n_farmer_pairs * self.FARMER_COST

        warrior_deficit = max(0, self.TARGET_WARRIORS - total_warriors)
        n_warrior_pairs = min(len(pool) // 2, budget // self.WARRIOR_COST, warrior_deficit)
        for c in pool[: 2 * n_warrior_pairs]:
            spawn_plan[id(c)] = "spawn warrior"

        # 3. Assign every villager to exactly one group.
        for c in components:
            cid = id(c)
            if cid in eater_ids:
                environment.assign_group(c, "eat")
            elif cid in spawn_plan:
                environment.assign_group(c, spawn_plan[cid])
            elif c.role == "Warrior" and c.steps_since_meal < self.WARRIOR_EAT_THRESHOLD:
                # Warriors with a fresh enough meal clock go (back) to the Cave.
                environment.assign_group(c, "cave")
            else:
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        # Farmers should never be here; send them home.
        for c in farmers:
            environment.assign_group(c, "village")

        attackers = []
        returners = []
        for c in warriors:
            # Warriors walk home to eat once their meal clock is high.
            if c.steps_since_meal >= self.CAVE_RETURN_THRESHOLD:
                returners.append(c)
            else:
                attackers.append(c)

        # Keep the Dragon attacked every step: if nobody is eligible,
        # keep the freshest warrior in the fight.
        if not attackers and returners:
            freshest = min(returners, key=lambda c: c.steps_since_meal)
            returners = [c for c in returners if c is not freshest]
            attackers.append(freshest)

        for c in attackers:
            environment.assign_group(c, "attack")
        for c in returners:
            environment.assign_group(c, "village")

        # Only warriors that stay in the Cave are counted here. Returners are
        # counted by the Village phase when they arrive.
        self._cave_attackers = len(attackers)