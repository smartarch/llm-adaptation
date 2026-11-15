from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Farmers stay in the Village (farm, eat, spawn).
    Warriors rotate through the Cave so that the Dragon is attacked
    almost every step, and each warrior returns to the Village to eat
    before it can starve.
    """

    VILLAGE_EAT_THRESHOLD = 1   # warriors arriving from the Cave eat right away
    FARMER_EAT_THRESHOLD = 3    # farmers eat before they get close to starving
    CAVE_RETURN_THRESHOLD = 3   # hungry warriors go home from the Cave at this hunger
    MAX_FALLBACK_HUNGER = 4     # a lone warrior may keep attacking up to this hunger
    TARGET_FARMERS = 4
    TARGET_WARRIORS = 3
    FARMER_SPAWN_COST = 10
    WARRIOR_SPAWN_COST = 12

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        assignments = {}

        # 1. Meals first (1 wheat each).
        # Warriors that arrived hungry eat, and warriors that just ate (hunger 0) go back to the Cave.
        for c in sorted(components, key=lambda c: -c.steps_since_meal):
            if c.role == "Warrior":
                needs_meal = c.steps_since_meal >= self.VILLAGE_EAT_THRESHOLD
            else:
                needs_meal = c.steps_since_meal >= self.FARMER_EAT_THRESHOLD
            if needs_meal and wheat >= 1:
                assignments[c] = "eat"
                wheat -= 1

        free = [c for c in components if c not in assignments]
        free_farmers = [c for c in free if c.role == "Farmer"]
        free_warriors = [c for c in free if c.role == "Warrior"]

        total_farmers = sum(1 for c in components if c.role == "Farmer")
        total_warriors = sum(1 for c in components if c.role == "Warrior")

        # 2. Spawn at most one pair per step, using only free farmers.
        if len(free_farmers) >= 2:
            if total_farmers < self.TARGET_FARMERS and wheat >= self.FARMER_SPAWN_COST:
                for c in free_farmers[:2]:
                    assignments[c] = "spawn farmer"
                free_farmers = free_farmers[2:]
                wheat -= self.FARMER_SPAWN_COST
            elif total_warriors < self.TARGET_WARRIORS and wheat >= self.WARRIOR_SPAWN_COST:
                for c in free_farmers[:2]:
                    assignments[c] = "spawn warrior"
                free_farmers = free_farmers[2:]
                wheat -= self.WARRIOR_SPAWN_COST

        # 3. Free warriors (fed) head to the Cave to attack.
        for c in free_warriors:
            assignments[c] = "cave"

        # 4. Everyone else farms.
        for c in free_farmers:
            assignments[c] = "farm"

        for c in components:
            environment.assign_group(c, assignments.get(c, "farm"))

    def assign_in_cave(self, components, environment, group_ids, step: int):
        assignments = {}
        warriors = [c for c in components if c.role == "Warrior"]

        # Farmers never fight: send them home.
        for c in components:
            if c.role == "Farmer":
                assignments[c] = "village"

        fed = [c for c in warriors if c.steps_since_meal < self.CAVE_RETURN_THRESHOLD]
        hungry = [c for c in warriors if c.steps_since_meal >= self.CAVE_RETURN_THRESHOLD]

        # Never leave the Dragon unattacked: if no fed warrior is here,
        # keep the least hungry one fighting while it is still safe.
        if not fed and hungry:
            best = min(hungry, key=lambda c: c.steps_since_meal)
            if best.steps_since_meal <= self.MAX_FALLBACK_HUNGER:
                hungry.remove(best)
                fed.append(best)

        for c in fed:
            assignments[c] = "attack"
        for c in hungry:
            assignments[c] = "village"

        for c in components:
            environment.assign_group(c, assignments.get(c, "cave"))