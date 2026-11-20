from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Economy-first eating with a later spawn window:
      - Every villager in the Village eats only at EAT_THRESHOLD steps without a
        meal (the last safe point before the 6-step starvation limit). This
        keeps farmers farming longer and saves wheat.
      - One farmer spawn early to satisfy the farmer requirement.
      - Idle farmer pairs spawn warriors until SPAWN_WARRIOR_UNTIL, limited by
        the wheat left after this step's meals.
      - Warriors in the Cave leave at RETURN_THRESHOLD (latest safe point for a
        walk back plus a meal). A warrior at FRAGILE_HP or less retreats to avoid
        dying to the next area attack.
      - Farmers farm in the Village and never enter the Cave.
    """

    EAT_THRESHOLD = 4          # village: eat when this many steps have passed
    RETURN_THRESHOLD = 4       # cave: leave at this hunger (latest safe point)
    FRAGILE_HP = 1             # cave: retreat at or below this HP
    SPAWN_WARRIOR_UNTIL = 20   # warriors spawned later have too little time to attack
    FARMER_COST = 10
    WARRIOR_COST = 12

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.farmer_spawned = False

    def _steps(self, c):
        return getattr(c, "steps_since_meal", 0)

    def _hp(self, c):
        return getattr(c, "hp", 6)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat

        eaters, rest = [], []
        for c in components:
            if self._steps(c) >= self.EAT_THRESHOLD:
                eaters.append(c)
            else:
                rest.append(c)

        # Budget wheat for this step's meals first.
        available = wheat - len(eaters)

        farmers = [c for c in rest if c.role == "Farmer"]

        spawn_assign = {}
        used = set()

        # One farmer spawn (requirement: at least one new farmer).
        if not self.farmer_spawned and len(farmers) >= 2 and available >= self.FARMER_COST:
            for c in farmers[:2]:
                spawn_assign[c] = "spawn farmer"
                used.add(c)
            available -= self.FARMER_COST
            self.farmer_spawned = True

        # Warrior spawning, limited by wheat and by the time left to attack.
        free_farmers = [c for c in farmers if c not in used]
        while step < self.SPAWN_WARRIOR_UNTIL \
                and len(free_farmers) >= 2 \
                and available >= self.WARRIOR_COST:
            pair = free_farmers[:2]
            free_farmers = free_farmers[2:]
            for c in pair:
                spawn_assign[c] = "spawn warrior"
                used.add(c)
            available -= self.WARRIOR_COST

        # Assign everyone.
        for c in components:
            if c in eaters:
                environment.assign_group(c, "eat")
            elif c in spawn_assign:
                environment.assign_group(c, spawn_assign[c])
            elif c.role == "Warrior":
                environment.assign_group(c, "cave")
            else:
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.role == "Farmer":
                environment.assign_group(c, "village")
            elif self._steps(c) >= self.RETURN_THRESHOLD:
                environment.assign_group(c, "village")
            elif self._hp(c) <= self.FRAGILE_HP:
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")