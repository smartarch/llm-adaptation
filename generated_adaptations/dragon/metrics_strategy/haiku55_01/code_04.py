from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    # Steps without a meal before a villager is sent to eat
    FARMER_EAT_AT = 3
    WARRIOR_EAT_AT = 2
    # A warrior in the Cave returns to the Village at this hunger level
    WARRIOR_RETURN_AT = 3
    # Warriors only raid when this fresh and at least this healthy
    WARRIOR_RAID_MAX_HUNGER = 1
    WARRIOR_MIN_HP = 3
    # Population goals
    TARGET_FARMERS_BOOT = 3
    TARGET_WARRIORS = 6
    TARGET_FARMERS_MAX = 4

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Number of warriors currently in the Cave (from the last cave assignment)
        self.cave_warriors = 0

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        budget = wheat
        handled = set()

        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]
        total_farmers = len(farmers)
        total_warriors = len(warriors) + self.cave_warriors

        # 1. Eating has priority: most-hungry first, limited by wheat
        needs_food = []
        for c in components:
            threshold = self.WARRIOR_EAT_AT if c.role == "Warrior" else self.FARMER_EAT_AT
            if c.steps_since_meal >= threshold:
                needs_food.append(c)
        for c in sorted(needs_food, key=lambda x: -x.steps_since_meal):
            if budget >= 1:
                environment.assign_group(c, "eat")
                budget -= 1
                handled.add(id(c))

        remaining = [c for c in components if id(c) not in handled]

        # 2. Fed, healthy warriors raid the Cave
        spare_warriors = []
        for c in remaining:
            if c.role == "Warrior":
                if c.steps_since_meal <= self.WARRIOR_RAID_MAX_HUNGER and c.hp >= self.WARRIOR_MIN_HP:
                    environment.assign_group(c, "cave")
                    handled.add(id(c))
                else:
                    spare_warriors.append(c)

        # 3. Spawning: needs a pair from the spawn group
        pool = [c for c in remaining if id(c) not in handled and c.role == "Farmer"]
        pool += [c for c in spare_warriors if c.role == "Warrior"]

        spawn_group = None
        if len(pool) >= 2:
            if total_farmers < self.TARGET_FARMERS_BOOT and budget >= 10:
                spawn_group = "spawn farmer"
                cost = 10
            elif total_warriors < self.TARGET_WARRIORS and budget >= 12:
                spawn_group = "spawn warrior"
                cost = 12
            elif total_farmers < self.TARGET_FARMERS_MAX and budget >= 10:
                spawn_group = "spawn farmer"
                cost = 10

        if spawn_group is not None:
            # Prefer farmers as the spawning pair so warriors keep fighting
            pool.sort(key=lambda c: 0 if c.role == "Farmer" else 1)
            for c in pool[:2]:
                environment.assign_group(c, spawn_group)
                handled.add(id(c))
            budget -= cost

        # 4. Everyone else stays in the Village and farms
        for c in components:
            if id(c) not in handled:
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        attackers = 0
        for c in components:
            if c.role == "Warrior":
                # Go home to eat before starving, or when badly wounded
                if c.steps_since_meal >= self.WARRIOR_RETURN_AT or c.hp <= 2:
                    environment.assign_group(c, "village")
                else:
                    environment.assign_group(c, "attack")
                    attackers += 1
            else:
                # Farmers never fight and would only take area damage
                environment.assign_group(c, "village")
        self.cave_warriors = sum(1 for c in components if c.role == "Warrior")