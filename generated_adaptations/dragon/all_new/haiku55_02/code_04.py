from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Strategy:
    - Hungry villagers (steps_since_meal >= HUNGER_LIMIT) eat first, but only
      as many as the wheat stock allows. Meals are never assigned without wheat.
    - Spawning uses only the wheat left after meals, minus a small reserve.
    - Early game: spawn farmers (cheap, produce 5 wheat/step) to build income.
      Later: spawn warriors for damage.
    - Fed warriors attack the Dragon from the Cave and return to the Village
      before they starve. Farmers stay on the farm.
    - Every component is assigned exactly once per call.
    """

    HUNGER_LIMIT = 3       # eat when steps_since_meal reaches this value
    MAX_WARRIORS = 8       # stop spawning warriors beyond this count
    MAX_FARMERS = 6        # stop spawning farmers beyond this count
    FARMER_COST = 10
    WARRIOR_COST = 12
    RESERVE = 2            # wheat kept aside for the next step's meals
    FARMER_PHASE_STEPS = 10  # spawn farmers for economy only in early steps

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        comps = list(components)
        wheat = environment.farm.wheat
        dragon_alive = environment.dragon.hp > 0

        assigned = set()

        # 1. Meals: feed the hungriest villagers first, as far as wheat allows.
        hungry = [i for i, c in enumerate(comps) if c.steps_since_meal >= self.HUNGER_LIMIT]
        hungry.sort(key=lambda i: comps[i].steps_since_meal, reverse=True)
        for i in hungry:
            if wheat >= 1:
                environment.assign_group(comps[i], "eat")
                assigned.add(i)
                wheat -= 1
        # Hungry villagers that could not be fed still need a group.
        for i in hungry:
            if i not in assigned:
                environment.assign_group(comps[i], "farm")
                assigned.add(i)

        # 2. Spawning from fed villagers, using only the leftover wheat.
        fed_farmers = [i for i, c in enumerate(comps)
                       if i not in assigned and c.role == "Farmer"]
        n_warriors = len(environment.warriors)
        n_farmers = len(environment.farmers)
        spare = wheat - self.RESERVE

        spawn_pair = None
        if dragon_alive and len(fed_farmers) >= 2:
            if (step < self.FARMER_PHASE_STEPS
                    and n_farmers < self.MAX_FARMERS
                    and spare >= self.FARMER_COST):
                spawn_pair = ("spawn farmer", fed_farmers[:2])
            elif (n_warriors < self.MAX_WARRIORS
                    and spare >= self.WARRIOR_COST):
                spawn_pair = ("spawn warrior", fed_farmers[:2])

        if spawn_pair is not None:
            group, idxs = spawn_pair
            for i in idxs:
                environment.assign_group(comps[i], group)
                assigned.add(i)

        # 3. Everyone else who is fed.
        for i, c in enumerate(comps):
            if i in assigned:
                continue
            if c.role == "Warrior" and dragon_alive:
                environment.assign_group(c, "cave")
            else:
                environment.assign_group(c, "farm")
            assigned.add(i)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.role == "Warrior" and c.steps_since_meal < self.HUNGER_LIMIT:
                # Healthy warriors keep hitting the Dragon.
                environment.assign_group(c, "attack")
            else:
                # Hungry warriors and farmers return to the Village.
                environment.assign_group(c, "village")