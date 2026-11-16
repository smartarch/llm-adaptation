## Diagnosis of the last run

The 100% win rate is a good sign, but winning took 25.7 steps on average, and the attack rate was too low:

1. **Too few attackers per step (1.5).** Warriors cycle between the Cave and the Village to eat, so much of the time they are in transit or eating. Attack power comes from how many warriors are in the Cave at once, not from how many exist.
2. **Spawning stopped too early.** Warriors spawned after step 22 would have had little time to attack. Only 7 warriors were spawned in total.
3. **Farmers were idle as spawners for too long, and the wheat reserve was too conservative.** A reserve of 2 on top of each cost blocked spawns that the wheat could have paid for.

## Revised strategy: Front-loaded warrior production

**Village phase**
- **Eat only when needed:** Villagers with `steps_since_meal >= 2` eat, which keeps warriors fresh for the next trip.
- **One early farmer spawn:** As before, a pair of idle farmers spawns one farmer to meet the requirement. This happens as soon as the wheat allows, with no reserve beyond the meals already budgeted.
- **Aggressive warrior spawning:** Every step until step 18, all idle farmer pairs go to "spawn warrior" as long as wheat covers the warrior cost (12) plus the meals already budgeted. The old cap of step 22 is gone, and the reserve is reduced to zero. Warriors spawned by step 18 still have time to attack.
- **Fed warriors go to the Cave immediately**, so a warrior returning from a meal re-enters the fight right away.
- **Farmers that are not spawning farm** to keep wheat income flowing.

**Cave phase**
- **Attack by default.** Warriors attack every step.
- **Return at 4 steps without a meal**, so a warrior still has one step to walk back and eat before the 6-step starvation limit.
- **Farmers are sent back to the Village** immediately.

Because warriors are produced earlier and in larger numbers, more of them are in the Cave at the same time. That raises damage per step and shortens the fight.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Front-loaded warrior production:
      - Idle farmer pairs spawn warriors every step until SPAWN_WARRIOR_UNTIL,
        limited only by wheat (no fixed reserve beyond the budgeted meals).
      - One farmer spawn early to satisfy the farmer requirement.
      - Fed warriors go to the Cave immediately; they attack every step and
        return only when hungry (steps_since_meal >= RETURN_THRESHOLD).
      - Farmers farm in the Village and never enter the Cave.
    """

    EAT_THRESHOLD = 2          # village: eat when this many steps have passed
    RETURN_THRESHOLD = 4       # cave: go back to village when this hungry
    SPAWN_WARRIOR_UNTIL = 18   # warriors spawned later would have too little time to attack
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

        # Each meal costs 1 wheat; budget for meals first.
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

        # Aggressive warrior spawning, limited only by wheat and time.
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
            else:
                environment.assign_group(c, "attack")
```