import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    # Eat when this many steps have passed without a meal (starvation at 6).
    EAT_THRESHOLD = 3
    # A Warrior in the Cave with at least this hunger goes back to eat.
    CAVE_RETURN_THRESHOLD = 3
    # Population targets.
    TARGET_FARMERS = 6
    TARGET_WARRIORS = 8
    # Wheat costs.
    WARRIOR_COST = 12
    FARMER_COST = 10

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Population estimate for villagers currently in the cave.
        self._cave_farmers = 0
        self._cave_warriors = 0

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        assigned = set()

        # 1. Eat first: villagers close to starving eat now.
        for c in components:
            if c.steps_since_meal >= self.EAT_THRESHOLD:
                environment.assign_group(c, "eat")
                assigned.add(c)
                wheat -= 1

        rest = [c for c in components if c not in assigned]
        village_farmers = [c for c in rest if c.role == "Farmer"]
        village_warriors = [c for c in rest if c.role == "Warrior"]

        # Estimated total population (village now + cave at last step).
        total_farmers = len([c for c in components if c.role == "Farmer"]) + self._cave_farmers
        total_warriors = len([c for c in components if c.role == "Warrior"]) + self._cave_warriors

        # 2. Breeding. Spawn groups need pairs of villagers; Farmers are used so Warriors keep attacking.
        pool = list(village_farmers)

        # Build the Farmer base first (cheap, pays back quickly).
        if total_farmers < self.TARGET_FARMERS and wheat >= self.FARMER_COST and len(pool) >= 2:
            max_pairs = min(len(pool) // 2,
                            wheat // self.FARMER_COST,
                            self.TARGET_FARMERS - total_farmers)
            n = max_pairs * 2
            for c in pool[:n]:
                environment.assign_group(c, "spawn farmer")
                assigned.add(c)
            pool = pool[n:]
            wheat -= max_pairs * self.FARMER_COST
            total_farmers += max_pairs

        # Then surge Warriors with any remaining Farmer pairs.
        if total_warriors < self.TARGET_WARRIORS and wheat >= self.WARRIOR_COST and len(pool) >= 2:
            max_pairs = min(len(pool) // 2,
                            wheat // self.WARRIOR_COST,
                            self.TARGET_WARRIORS - total_warriors)
            n = max_pairs * 2
            for c in pool[:n]:
                environment.assign_group(c, "spawn warrior")
                assigned.add(c)
            pool = pool[n:]
            wheat -= max_pairs * self.WARRIOR_COST
            total_warriors += max_pairs

        # 3. Warriors that are not hungry go to the Cave to attack.
        cave_sent_warriors = 0
        for c in village_warriors:
            if c in assigned:
                continue
            environment.assign_group(c, "cave")
            assigned.add(c)
            cave_sent_warriors += 1

        # 4. Everyone else (remaining Farmers) farms.
        for c in components:
            if c in assigned:
                continue
            environment.assign_group(c, "farm")
            assigned.add(c)

        # Keep the population estimate in step with what was just assigned.
        self._cave_warriors += cave_sent_warriors

    def assign_in_cave(self, components, environment, group_ids, step: int):
        farmers = 0
        warriors = 0
        for c in components:
            if c.role == "Farmer":
                # Farmers never fight; they return to the Village.
                environment.assign_group(c, "village")
                farmers += 1
            elif c.steps_since_meal >= self.CAVE_RETURN_THRESHOLD:
                # Hungry Warriors go back to eat before attacking again.
                environment.assign_group(c, "village")
                warriors += 1
            else:
                # Healthy Warriors keep attacking the Dragon every step.
                environment.assign_group(c, "attack")
                warriors += 1
        self._cave_farmers = farmers
        self._cave_warriors = warriors