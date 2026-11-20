## Diagnosis of the last run

The win rate stayed at 33%, and the Dragon went unattacked for 4 steps on average. Looking across the runs, a few patterns stand out:

1. **Early departures cost attack time.** Leaving the Cave at hunger 3 wastes steps. The run with a 100% win rate left at hunger 4, which is the latest safe point for a 1-step walk plus a meal before the 6-step starvation limit.
2. **Cohort splitting and attacker-count guards added instability.** Splitting warriors by list position, and holding some back to keep a minimum attacker count, both made the Cave's attack rate less predictable. The guard also kept hungry warriors in the Cave longer than was safe.
3. **Fragile warriors were lost to area attacks.** The Dragon's 40% area hit does 1 damage to every villager in the Cave. A warrior at 1 HP dies on the next hit, so it is worth more alive in the Village, where it can still help later.
4. **Evaluation noise.** With only 3 games per evaluation, a 33% vs 100% swing is within the range of luck. I am not changing the core timing, which matched the best-performing run.

## Revised strategy: Latest-safe return with HP-aware retreat

- **Spawn early and in full.** Idle farmer pairs spawn warriors every step until step 18, limited only by the wheat left after this step's meals. This gives the largest attacking army as early as possible.
- **One farmer spawn** is still made early to meet the farmer requirement.
- **Eat at 2 steps in the Village**, and fed warriors return to the Cave immediately.
- **Leave the Cave at hunger 4**, the latest point that still allows a walk back and a meal before starvation. No cohort splitting and no attacker-count guard.
- **Retreat only when fragile.** A warrior at 1 HP in the Cave leaves for the Village. It is likely to die to the next area hit, and it can rejoin later. Warriors at 2 HP or more keep attacking.
- **Farmers farm** in the Village and never enter the Cave.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Latest-safe return with HP-aware retreat:
      - Idle farmer pairs spawn warriors until SPAWN_WARRIOR_UNTIL, limited by
        wheat left after this step's meals.
      - One farmer spawn early to satisfy the farmer requirement.
      - Villagers eat in the Village at EAT_THRESHOLD steps; fed warriors return
        to the Cave immediately.
      - In the Cave, warriors leave at hunger RETURN_THRESHOLD (the latest point
        that still allows a walk back and a meal before starvation).
      - Warriors at FRAGILE_HP or less retreat to the Village to avoid being
        killed by the next area attack; they rejoin after eating.
      - Farmers farm in the Village and never enter the Cave.
    """

    EAT_THRESHOLD = 2          # village: eat when this many steps have passed
    RETURN_THRESHOLD = 4       # cave: leave at this hunger (latest safe point)
    FRAGILE_HP = 1             # cave: retreat at or below this HP
    SPAWN_WARRIOR_UNTIL = 18   # warriors spawned later have too little time to attack
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