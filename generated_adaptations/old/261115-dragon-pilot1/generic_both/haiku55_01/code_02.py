from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    # Farmers and warriors must eat before they reach 6 steps without food.
    FARMER_EAT_THRESHOLD = 4
    # Warriors in the Cave return to the Village at this meal-clock value.
    CAVE_RETURN_THRESHOLD = 2
    # Target population used to decide what to spawn.
    MIN_FARMERS = 2
    MIN_WARRIORS = 4

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # 1. Decide who eats this step (food is priority, it costs 1 wheat each).
        eaters = []
        non_eaters = []
        for c in components:
            if c.role == "Farmer":
                needs_food = c.steps_since_meal >= self.FARMER_EAT_THRESHOLD
            else:
                # Warriors eat whenever they are in the Village and not fresh,
                # so they can leave for the Cave with a meal clock near 0.
                needs_food = c.steps_since_meal >= 1
            if needs_food:
                eaters.append(c)
            else:
                non_eaters.append(c)

        wheat_after_meals = wheat - len(eaters)

        # 2. Choose spawning (uses idle, non-eating villagers as the spawn pair).
        spawn_pair = []
        spawn_group = None
        idle_farmers = [c for c in non_eaters if c.role == "Farmer"]
        idle_warriors = [c for c in non_eaters if c.role == "Warrior"]

        if len(farmers) < self.MIN_FARMERS and wheat_after_meals >= 10 and len(non_eaters) >= 2:
            spawn_group = "spawn farmer"
            pool = idle_farmers if len(idle_farmers) >= 2 else non_eaters
            spawn_pair = pool[:2]
        elif len(warriors) < self.MIN_WARRIORS and wheat_after_meals >= 12 and len(non_eaters) >= 2:
            spawn_group = "spawn warrior"
            pool = idle_farmers if len(idle_farmers) >= 2 else non_eaters
            spawn_pair = pool[:2]

        spawn_ids = {id(c) for c in spawn_pair}

        # 3. Assign each villager to exactly one group.
        for c in components:
            if c in eaters:
                environment.assign_group(c, "eat")
            elif spawn_group is not None and id(c) in spawn_ids:
                environment.assign_group(c, spawn_group)
            elif c.role == "Warrior" and c.steps_since_meal == 0:
                # Fresh warriors go to the Cave to attack.
                environment.assign_group(c, "cave")
            else:
                # Farmers (and any warrior not yet ready) keep farming.
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
            # Hungry warriors go home to eat before they starve.
            if c.steps_since_meal >= self.CAVE_RETURN_THRESHOLD:
                returners.append(c)
            else:
                attackers.append(c)

        # Keep the Dragon attacked every step: if nobody is eligible,
        # keep the freshest warrior in the fight.
        if not attackers and returners:
            freshest = min(returners, key=lambda c: c.steps_since_meal)
            returners.remove(freshest)
            attackers.append(freshest)

        for c in attackers:
            environment.assign_group(c, "attack")
        for c in returners:
            environment.assign_group(c, "village")