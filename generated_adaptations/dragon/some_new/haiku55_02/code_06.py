from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Strategy:
    - In the Village, hungry villagers (steps_since_meal >= 3) eat, but only as many
      as the available wheat allows (most hungry first). Unfed hungry villagers stay
      on the farm and are excluded from spawning.
    - Spawning uses pairs of fed, ready villagers (farmers first):
        * 'spawn warrior' while total warriors < WARRIOR_TARGET and wheat allows;
        * early in the game, 'spawn farmer' to grow the wheat economy.
      Wheat reserved for meals is subtracted before any spawn.
    - Remaining fed warriors go to the Cave and attack while steps_since_meal <= 2.
    - In the Cave, warriors with steps_since_meal >= 3 and all farmers return to the Village.
    - Every component is assigned exactly once in every call.
    """

    EAT_THRESHOLD = 3          # eat in village when hunger reaches this
    RETURN_THRESHOLD = 3       # leave cave to eat when hunger reaches this
    WARRIOR_TARGET = 8         # total warriors we want alive
    FARMER_TARGET = 6          # total farmers we want alive
    EARLY_FARMER_STEP = 10     # farmer spawning only in early game

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        total_warriors = len(environment.warriors)
        total_farmers = len(environment.farmers)

        # Hungry villagers, most hungry first
        hungry = sorted(
            [c for c in components if c.steps_since_meal >= self.EAT_THRESHOLD],
            key=lambda c: -c.steps_since_meal,
        )
        # Only feed as many as the wheat stock allows (1 wheat per meal)
        n_eat = max(0, min(len(hungry), wheat))
        eaters = hungry[:n_eat]
        unfed = hungry[n_eat:]

        wheat_avail = wheat - n_eat

        # Fed, ready villagers are the only candidates for spawning or the cave
        ready = [c for c in components if c.steps_since_meal < self.EAT_THRESHOLD]
        ready_farmers = [c for c in ready if c.role == "Farmer"]
        ready_warriors = [c for c in ready if c.role == "Warrior"]

        assignment = {}
        for c in eaters:
            assignment[id(c)] = "eat"
        for c in unfed:
            assignment[id(c)] = "farm"

        spawn_members = []
        spawn_group = None

        # Prefer spawning a warrior (12 wheat) while below the warrior target
        if total_warriors < self.WARRIOR_TARGET and wheat_avail >= 12:
            pool = ready_farmers + ready_warriors
            if len(pool) >= 2:
                spawn_members = pool[:2]
                spawn_group = "spawn warrior"
                wheat_avail -= 12

        # Otherwise, early in the game, grow the economy with a farmer (10 wheat)
        if spawn_group is None and step <= self.EARLY_FARMER_STEP \
                and total_farmers < self.FARMER_TARGET and wheat_avail >= 10:
            pool = ready_farmers + ready_warriors
            if len(pool) >= 2:
                spawn_members = pool[:2]
                spawn_group = "spawn farmer"
                wheat_avail -= 10

        spawn_ids = set(id(c) for c in spawn_members)
        for c in spawn_members:
            assignment[id(c)] = spawn_group

        for c in ready:
            if id(c) in spawn_ids:
                continue
            if c.role == "Warrior":
                assignment[id(c)] = "cave"
            else:
                assignment[id(c)] = "farm"

        # Every component is assigned exactly once
        for c in components:
            environment.assign_group(c, assignment[id(c)])

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.role != "Warrior" or c.steps_since_meal >= self.RETURN_THRESHOLD:
                environment.assign_group(c, "village")
            elif c.hp > 0:
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "cave")