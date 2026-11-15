from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Farmers stay in the Village (farm, eat, spawn).
    Warriors fight in the Cave and return to the Village to eat
    before they can starve.
    """

    EAT_THRESHOLD = 2          # eat early so the 6-step starvation limit is never reached
    CAVE_RETURN_THRESHOLD = 2  # warriors at/above this hunger go home from the Cave
    MAX_FALLBACK_HUNGER = 3    # a hungry warrior may stay to keep the Dragon attacked only this long
    TARGET_FARMERS = 4
    TARGET_WARRIORS = 3
    FARMER_SPAWN_COST = 10
    WARRIOR_SPAWN_COST = 12

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        assignments = {}

        # 1. Meals first: everyone at or above the eat threshold eats (1 wheat each).
        hungry = sorted(
            [c for c in components if c.steps_since_meal >= self.EAT_THRESHOLD],
            key=lambda c: -c.steps_since_meal,
        )
        for c in hungry:
            if wheat >= 1:
                assignments[c] = "eat"
                wheat -= 1
            else:
                assignments[c] = "farm"  # cannot eat; nothing else can help

        # 2. Remaining (fed) villagers.
        free = [c for c in components if c not in assignments]
        free_farmers = [c for c in free if c.role == "Farmer"]
        free_warriors = [c for c in free if c.role == "Warrior"]

        total_farmers = sum(1 for c in components if c.role == "Farmer")
        total_warriors = sum(1 for c in components if c.role == "Warrior")

        # 3. Spawn at most one pair per step, using only fed farmers.
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

        # 4. Fed warriors go to the Cave to attack.
        for c in free_warriors:
            assignments[c] = "cave"

        # 5. Everyone else farms.
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

        # Keep the Dragon attacked: if no fed warrior is left, keep the least
        # hungry one fighting, but only while it is still safe to do so.
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