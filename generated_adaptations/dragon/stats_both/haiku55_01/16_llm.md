## Diagnosis of the last run

The win rate is still 33%, and the Dragon went unattacked for about 4 steps. Attack capacity remains the bottleneck, but the logs point to a cause I had overlooked:

1. **Farmers spent most of their time eating.** The village eat threshold of 2 applies to farmers too. Every 2 or 3 steps a farmer leaves the "farm" group to eat, so it produces no wheat during that step. Wheat income is therefore well below 3 farmers × 5 per step, and warrior spawning is limited by wheat.
2. **Meal budget was too generous.** Eating more often than needed costs wheat that could have paid for warriors.
3. **Warrior spawning stopped at step 18.** With a wheat shortage, warriors arrived too late to deal much damage.

## Revised strategy: Economy-first eating and a later spawn window

- **Eat at the last safe point.** Every villager in the Village eats at `steps_since_meal >= 4`. That still leaves a margin before the 6-step starvation limit, and it cuts the time farmers spend eating, so more of them farm.
- **Warriors return at hunger 4 as before.** A warrior that leaves the Cave at hunger 4 reaches the Village at hunger 5, so it eats on arrival. The cycle is unchanged.
- **Keep the early farmer spawn.** It meets the farmer requirement and adds wheat income sooner.
- **Extend warrior spawning to step 20.** Spawning is still limited by wheat after this step's meals.
- **Retreat at 1 HP.** Keeps the fragile-warrior rule from the last version.

The main change is the lower eating frequency. It frees up wheat and farming time, which should let more warriors be spawned and more attackers reach the Cave.

```py
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
```