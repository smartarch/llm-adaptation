from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    # Farmers must eat before they reach 6 steps without food.
    FARMER_EAT_THRESHOLD = 4
    # Warriors eat in the Village once their meal clock reaches this value.
    WARRIOR_EAT_THRESHOLD = 3
    # Warriors in the Cave walk home once their meal clock reaches this value.
    CAVE_RETURN_THRESHOLD = 4
    # Target population. More farmers produce more wheat for warrior spawns.
    TARGET_FARMERS = 4
    TARGET_WARRIORS = 10
    FARMER_COST = 10
    WARRIOR_COST = 12

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Warriors currently in the Cave, updated during assign_in_cave.
        self._cave_warriors = 0

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
        wheat_budget = wheat - len(eaters)

        non_eaters = [c for c in components if id(c) not in eater_ids]
        idle_farmers = [c for c in non_eaters if c.role == "Farmer"]

        # 2. Decide spawning. Each spawn group needs an even number of villagers;
        #    every pair of villagers in the group spawns one new villager.
        spawn_group = None
        spawn_ids = set()

        total_farmers = len(farmers)
        total_warriors = len(warriors) + self._cave_warriors

        if total_farmers < self.TARGET_FARMERS:
            cost = self.FARMER_COST
            deficit = self.TARGET_FARMERS - total_farmers
            spawn_group = "spawn farmer"
        elif total_warriors < self.TARGET_WARRIORS:
            cost = self.WARRIOR_COST
            deficit = self.TARGET_WARRIORS - total_warriors
            spawn_group = "spawn warrior"
        else:
            cost = None
            deficit = 0

        if cost is not None and deficit > 0:
            n_pairs = min(
                len(idle_farmers) // 2,
                wheat_budget // cost,
                deficit,
            )
            if n_pairs > 0:
                spawn_ids = {id(c) for c in idle_farmers[: 2 * n_pairs]}
            else:
                spawn_group = None

        # 3. Assign every villager to exactly one group.
        for c in components:
            cid = id(c)
            if cid in eater_ids:
                environment.assign_group(c, "eat")
            elif spawn_group is not None and cid in spawn_ids:
                environment.assign_group(c, spawn_group)
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

        # Remember how many warriors are in the Cave for the next village decision.
        # Warriors walking home are not counted, since they are still part of the army.
        self._cave_warriors = len(warriors)