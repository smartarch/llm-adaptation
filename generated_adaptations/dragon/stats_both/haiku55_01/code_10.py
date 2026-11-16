from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Staggered-cohort strategy:
      - Idle farmer pairs spawn warriors until SPAWN_WARRIOR_UNTIL, limited only
        by wheat left after this step's meals.
      - One farmer spawn early to satisfy the farmer requirement.
      - Warriors eat in the Village at EAT_THRESHOLD steps and then return to
        the Cave immediately.
      - In the Cave, warriors are split into two cohorts with different return
        thresholds (3 or 4 steps hungry), so they do not all leave at once and
        the Dragon is attacked on most steps.
      - Farmers farm in the Village and never enter the Cave.
    """

    EAT_THRESHOLD = 2          # village: eat when this many steps have passed
    RETURN_THRESHOLD_A = 3     # cave cohort A: return at this hunger
    RETURN_THRESHOLD_B = 4     # cave cohort B: return at this hunger
    SPAWN_WARRIOR_UNTIL = 18   # warriors spawned later have too little time to attack
    FARMER_COST = 10
    WARRIOR_COST = 12

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.farmer_spawned = False

    def _steps(self, c):
        return getattr(c, "steps_since_meal", 0)

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
        for i, c in enumerate(components):
            if c.role == "Farmer":
                environment.assign_group(c, "village")
                continue
            # Stagger the two cohorts so their return trips do not coincide.
            threshold = self.RETURN_THRESHOLD_A if i % 2 == 0 else self.RETURN_THRESHOLD_B
            if self._steps(c) >= threshold:
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")