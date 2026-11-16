## Diagnosis of the last run

The win rate is back to 33%, and the Dragon went unattacked for 6.7 steps on average. Attack capacity is still the bottleneck, with about 1.3 attackers per step.

1. **Cohorts leave by fixed index.** Splitting warriors by list position is arbitrary. In some steps almost every warrior hits the return threshold together, which empties the Cave.
2. **Early departures waste attack steps.** A warrior that leaves at hunger 3 spends about 3 steps in transit or eating for every 3 steps of attacking. Some of that time is unnecessary when enough other warriors are still able to attack.
3. **No guard on the attacker count.** Nothing ensures that a minimum number of warriors keep attacking.

## Revised strategy: Demand-aware return

- **Keep the spawn schedule.** Idle farmer pairs spawn warriors until step 18, limited by wheat after this step's meals. The farmer requirement is met with one early spawn.
- **Eat at 2 steps in the Village**, and send fed warriors back to the Cave at once.
- **Return based on how many attackers remain.** In the Cave, warriors at hunger 4 or more always leave, since they must be back in the Village before the 6-step limit. Warriors at hunger 3 leave only if enough other warriors would still attack. Otherwise they stay and keep attacking, and they leave at hunger 4 at the latest.
- **Attack rate target.** The rule keeps at least `MIN_ATTACKERS` warriors in the Cave whenever possible, so the Dragon is hit on nearly every step, including while warriors are walking or eating.
- **Farmers never enter the Cave** and keep farming for meal and spawn wheat.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Demand-aware return strategy:
      - Idle farmer pairs spawn warriors until SPAWN_WARRIOR_UNTIL, limited by
        the wheat left after this step's meals.
      - One farmer spawn early to satisfy the farmer requirement.
      - Villagers eat in the Village at EAT_THRESHOLD steps; fed warriors go
        straight back to the Cave.
      - In the Cave, warriors at hunger >= MUST_LEAVE leave unconditionally.
        Warriors at hunger == SOFT_LEAVE leave only if at least MIN_ATTACKERS
        warriors would still be attacking, so the Dragon is attacked whenever
        possible.
      - Farmers farm in the Village and never enter the Cave.
    """

    EAT_THRESHOLD = 2          # village: eat when this many steps have passed
    SOFT_LEAVE = 3             # cave: leave at this hunger only if enough attackers remain
    MUST_LEAVE = 4             # cave: leave at this hunger no matter what
    MIN_ATTACKERS = 3          # keep at least this many warriors attacking when possible
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
        warriors = [c for c in components if c.role == "Warrior"]

        # Farmers never stay in the Cave.
        for c in components:
            if c.role == "Farmer":
                environment.assign_group(c, "village")

        # Warriors that must leave now.
        must = [c for c in warriors if self._steps(c) >= self.MUST_LEAVE]
        # Warriors at the soft threshold; they leave only if enough attackers remain.
        soft = [c for c in warriors
                if self.SOFT_LEAVE <= self._steps(c) < self.MUST_LEAVE]
        # Everyone else keeps attacking.
        fresh = [c for c in warriors if self._steps(c) < self.SOFT_LEAVE]

        # Sort soft-threshold warriors so the most hungry leave first.
        soft.sort(key=lambda c: -self._steps(c))

        attackers = len(fresh)
        stay_soft = []
        leave_soft = []
        for c in soft:
            if attackers + len(stay_soft) < self.MIN_ATTACKERS:
                stay_soft.append(c)
            else:
                leave_soft.append(c)

        for c in must + leave_soft:
            environment.assign_group(c, "village")
        for c in fresh + stay_soft:
            environment.assign_group(c, "attack")
```