import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Village:
      - Villagers with steps_since_meal >= HUNGER_THRESHOLD eat first (most hungry first),
        as long as wheat is available for the meal.
      - Hungry warriors that cannot be fed stay in the village (never sent to the cave).
      - Fed warriors go back to the cave to attack the dragon.
      - Free farmers spawn warriors, then farmers, only from a wheat surplus that also
        covers the next round of meals. Other farmers keep farming so wheat is produced.
    Cave:
      - Farmers go back to the village.
      - At most one warrior is away from the cave at a time, so the dragon keeps
        being attacked. A warrior leaves for food at LEAVE_THRESHOLD only if no other
        warrior is away and at least one warrior stays in the cave.
      - A warrior at FORCE_LEAVE_THRESHOLD leaves regardless, so it never starves.
    Every component is assigned exactly once per call.
    """

    HUNGER_THRESHOLD = 3        # village: eat when this many steps have passed without a meal
    LEAVE_THRESHOLD = 3         # cave: leave for food at this hunger
    FORCE_LEAVE_THRESHOLD = 4   # cave: a warrior must leave for food at this hunger
    MIN_SPAWNS = 2              # at least this many of each role should be spawned
    WARRIOR_COST = 12
    FARMER_COST = 10

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.spawned_farmers = 0
        self.spawned_warriors = 0
        self.last_village_warriors = 0   # warriors seen in the village at the last village step
        self.last_cave_warriors = 0      # warriors seen in the cave at the last cave step

    # ------------------------------------------------------------------ village
    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = int(environment.farm.wheat)
        plan = {}  # id(component) -> group

        self.last_village_warriors = sum(1 for c in components if c.role == "Warrior")

        # 1) Hungry villagers eat first, most hungry first, limited by wheat
        budget = max(0, wheat)
        hungry = sorted(
            [c for c in components if c.steps_since_meal >= self.HUNGER_THRESHOLD],
            key=lambda c: c.steps_since_meal,
            reverse=True,
        )
        for c in hungry:
            if budget > 0:
                plan[id(c)] = "eat"
                budget -= 1
            else:
                # cannot be fed: never send a hungry warrior to the cave
                plan[id(c)] = "farm"
        wheat_after_meals = budget

        # 2) Fed villagers
        free_farmers = []
        for c in components:
            if id(c) in plan:
                continue
            if c.role == "Warrior":
                plan[id(c)] = "cave"        # fed warriors attack the dragon
            else:
                free_farmers.append(c)

        # 3) Spawning, only from a surplus that still covers the next round of meals
        reserve = len(components)           # about one meal per villager
        remaining = wheat_after_meals

        if (self.spawned_warriors < self.MIN_SPAWNS
                and len(free_farmers) >= 2
                and remaining - self.WARRIOR_COST >= reserve):
            for c in free_farmers[:2]:
                plan[id(c)] = "spawn warrior"
            free_farmers = free_farmers[2:]
            remaining -= self.WARRIOR_COST
            self.spawned_warriors += 1

        if (self.spawned_farmers < self.MIN_SPAWNS
                and len(free_farmers) >= 2
                and remaining - self.FARMER_COST >= reserve):
            for c in free_farmers[:2]:
                plan[id(c)] = "spawn farmer"
            free_farmers = free_farmers[2:]
            remaining -= self.FARMER_COST
            self.spawned_farmers += 1

        # Remaining farmers keep farming so wheat keeps coming in
        for c in free_farmers:
            plan[id(c)] = "farm"

        # 4) Apply exactly once per component
        for c in components:
            environment.assign_group(c, plan[id(c)])

    # --------------------------------------------------------------------- cave
    def assign_in_cave(self, components, environment, group_ids, step: int):
        plan = {}
        warriors = []
        for c in components:
            if c.role == "Warrior":
                warriors.append(c)
            else:
                plan[id(c)] = "village"     # farmers must not stay in the cave

        # Warriors not in the cave (eating or in transit), estimated from the latest village step
        away = self.last_village_warriors
        self.last_cave_warriors = len(warriors)

        ordered = sorted(warriors, key=lambda c: c.steps_since_meal, reverse=True)
        remaining = len(warriors)
        leaving = set()

        for w in ordered:
            s = w.steps_since_meal
            if s >= self.FORCE_LEAVE_THRESHOLD:
                leaving.add(id(w))          # about to starve: must go eat
                remaining -= 1
                away += 1
            elif s >= self.LEAVE_THRESHOLD and away == 0 and remaining - 1 >= 1:
                # only one warrior away at a time, and someone stays to attack
                leaving.add(id(w))
                remaining -= 1
                away += 1

        # Never leave the cave empty unless someone is forced to eat
        if warriors and remaining == 0:
            least = min(warriors, key=lambda c: c.steps_since_meal)
            if least.steps_since_meal < self.FORCE_LEAVE_THRESHOLD:
                leaving.discard(id(least))

        for w in warriors:
            plan[id(w)] = "village" if id(w) in leaving else "attack"

        # Apply exactly once per component
        for c in components:
            environment.assign_group(c, plan[id(c)])