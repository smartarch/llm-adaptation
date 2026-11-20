from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Warrior surge with a meal reserve:
      - Villagers eat at 2 steps without a meal, leaving slack for delays.
      - Before any spawn, wheat is reserved for meals due within the next two steps.
      - Warriors are spawned from Farmer pairs only from wheat above that reserve.
      - Warriors attack in the Cave and return at 3 steps without a meal.
      - Farmers stay in the Village to farm and never leave for the Cave.
    """

    EAT_THRESHOLD = 2           # Village: eat when this many steps have passed without a meal
    RESERVE_LOOKAHEAD = 2       # reserve wheat for villagers whose meal is due within this many steps
    CAVE_RETURN_THRESHOLD = 3   # Cave: Warriors go home at this point
    WARRIOR_COST = 12

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        dragon_alive = environment.dragon.hp > 0

        # Villagers whose meal is due soon must be fed; reserve wheat for them
        due_now = [c for c in components
                   if c.steps_since_meal >= self.EAT_THRESHOLD]
        due_soon = [c for c in components
                    if self.EAT_THRESHOLD > c.steps_since_meal
                    >= self.EAT_THRESHOLD - self.RESERVE_LOOKAHEAD]
        reserve = len(due_now) + len(due_soon)

        budget = wheat
        eaters = []
        for c in due_now:
            if budget >= 1:
                eaters.append(c)
                budget -= 1
        eat_ids = set(id(c) for c in eaters)
        rest = [c for c in components if id(c) not in eat_ids]

        free_farmers = [c for c in rest if c.role == "Farmer"]
        free_warriors = [c for c in rest if c.role == "Warrior"]

        spawn_warrior = []

        # Warrior surge: spawn only from wheat above the meal reserve
        if dragon_alive:
            spendable = budget - reserve
            while len(free_farmers) >= 2 and spendable >= self.WARRIOR_COST:
                spawn_warrior.extend([free_farmers.pop(), free_farmers.pop()])
                spendable -= self.WARRIOR_COST

        # Free Warriors head to the Cave; everyone else farms
        to_cave = list(free_warriors) if dragon_alive else []
        farming = free_farmers + ([] if dragon_alive else free_warriors)

        for c in eaters:
            environment.assign_group(c, "eat")
        for c in spawn_warrior:
            environment.assign_group(c, "spawn warrior")
        for c in to_cave:
            environment.assign_group(c, "cave")
        for c in farming:
            environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            # Farmers go home to farm; Warriors go home when a meal is due
            if c.role == "Farmer" or c.steps_since_meal >= self.CAVE_RETURN_THRESHOLD:
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")