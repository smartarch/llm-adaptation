from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Heuristic strategy:
      - Villagers that have not eaten for >= EAT_THRESHOLD steps eat first.
      - Farmers are used as spawners (so warriors keep attacking):
          * one farmer pair spawns a Farmer early (required at least once),
          * farmer pairs spawn Warriors early while wheat allows.
      - Remaining warriors go to the Cave and attack; remaining farmers farm.
      - In the Cave, warriors that are getting hungry return to the Village,
        others attack; farmers are sent back to the Village.
    """

    EAT_THRESHOLD = 3          # village: eat when this many steps have passed without a meal
    CAVE_RETURN_THRESHOLD = 4  # cave: go back to village when this hungry
    MAX_WARRIOR_SPAWN_STEP = 20
    MAX_WARRIOR_SPAWNS = 3
    FARMER_COST = 10
    WARRIOR_COST = 12

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.farmer_spawned = False
        self.warrior_spawns = 0

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        available = wheat

        eaters = []
        rest = []
        for c in components:
            if c.steps_since_meal >= self.EAT_THRESHOLD:
                eaters.append(c)
                available -= 1  # each meal consumes 1 wheat
            else:
                rest.append(c)

        farmers = [c for c in rest if c.role == "Farmer"]
        warriors = [c for c in rest if c.role == "Warrior"]

        spawn_assign = {}   # component -> group id for spawners
        used = set()

        # Spawn one new farmer (required at least once).
        if not self.farmer_spawned and len(farmers) >= 2 and available >= self.FARMER_COST:
            pair = farmers[:2]
            for c in pair:
                spawn_assign[c] = "spawn farmer"
                used.add(c)
            available -= self.FARMER_COST
            self.farmer_spawned = True

        # Spawn new warriors early in the game (farmers act as spawners).
        free_farmers = [c for c in farmers if c not in used]
        while (step < self.MAX_WARRIOR_SPAWN_STEP
               and self.warrior_spawns < self.MAX_WARRIOR_SPAWNS
               and len(free_farmers) >= 2
               and available >= self.WARRIOR_COST):
            pair = free_farmers[:2]
            free_farmers = free_farmers[2:]
            for c in pair:
                spawn_assign[c] = "spawn warrior"
                used.add(c)
            available -= self.WARRIOR_COST
            self.warrior_spawns += 1

        # Assign everyone.
        for c in components:
            if c in eaters:
                environment.assign_group(c, "eat")
            elif c in spawn_assign:
                environment.assign_group(c, spawn_assign[c])
            elif c.role == "Warrior":
                # Warriors with enough food go to the Cave to attack.
                environment.assign_group(c, "cave")
            else:
                # Farmers stay in the Village and produce wheat.
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.role == "Farmer":
                # Farmers must stay in the Village.
                environment.assign_group(c, "village")
            elif c.steps_since_meal >= self.CAVE_RETURN_THRESHOLD:
                # Hungry warriors go back to eat before they starve.
                environment.assign_group(c, "village")
            else:
                # Keep attacking the Dragon to prevent its regeneration.
                environment.assign_group(c, "attack")