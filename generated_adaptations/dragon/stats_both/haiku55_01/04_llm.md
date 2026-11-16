## Diagnosis

The previous run lost for three reasons:

1. **Too little damage.** Warriors averaged only 0.7 attackers per step, and the Dragon was left unattacked for about 15 steps. Its regeneration of 5 HP per unattacked step undid most of the progress.
2. **Warriors were lost to the Dragon.** All warriors died, and the Dragon killed 4 villagers. The old cave logic kept warriors in the cave until they were nearly starving, and the 40%/20% Dragon attacks picked them off.
3. **Too few warriors were spawned early.** Spawning was capped at 3 warriors, and they were used only briefly.

## Revised strategy: Continuous attack with staggered meal trips

**Village phase**
- **Eat when needed:** Any villager with `steps_since_meal >= 2` eats. Warriors returning from the cave therefore eat right away and go back with a fresh meal.
- **Spawn warriors aggressively:** Idle farmers form pairs for "spawn warrior" whenever wheat covers the cost plus a small reserve for the meals of the following steps. This continues for the first ~20 steps, with no fixed cap of 3. One farmer pair also spawns a farmer early to satisfy the farmer requirement.
- **Warriors go to the cave:** Every warrior that has just eaten (`steps_since_meal < 2`) goes to the "cave" group.
- **Farmers farm:** Remaining farmers stay on "farm" to keep wheat coming in.

**Cave phase**
- **Attack by default:** Every warrior attacks, keeping the Dragon under pressure and preventing regeneration.
- **Return only when hungry:** A warrior returns to the "village" group once `steps_since_meal >= 4`. That leaves a 1-step trip plus a meal before the 6-step starvation limit. Because warriors are spawned and sent at different times, their meal trips are naturally staggered, so the Dragon is attacked most steps.
- **Farmers never stay in the cave:** Any farmer found in the cave is sent to "village".

This keeps the attack rate high from the start, builds a much larger warrior force, and avoids starvation.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Continuous-pressure strategy:
      - Warriors are mass-spawned early (paid by idle farmer pairs) to build
        a large attack force quickly.
      - Warriors attack every step in the Cave and only leave when they are
        hungry (steps_since_meal >= RETURN_THRESHOLD), so the Dragon is
        attacked almost every step and does not regenerate.
      - Warriors that are in the Village and hungry eat immediately; fed
        warriors return to the Cave.
      - One farmer pair spawns a farmer early (requirement); farmers otherwise farm.
    """

    EAT_THRESHOLD = 2          # village: eat when this many steps have passed
    RETURN_THRESHOLD = 4       # cave: go back to village when this hungry
    SPAWN_WARRIOR_UNTIL = 22   # stop spawning warriors after this step
    FARMER_COST = 10
    WARRIOR_COST = 12
    RESERVE = 2                # wheat kept back for upcoming meals

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

        available = wheat - len(eaters)  # each meal costs 1 wheat

        farmers = [c for c in rest if c.role == "Farmer"]
        warriors = [c for c in rest if c.role == "Warrior"]

        spawn_assign = {}
        used = set()

        # One farmer spawn (requirement: at least one new farmer).
        if not self.farmer_spawned and len(farmers) >= 2 \
                and available >= self.FARMER_COST + self.RESERVE:
            for c in farmers[:2]:
                spawn_assign[c] = "spawn farmer"
                used.add(c)
            available -= self.FARMER_COST
            self.farmer_spawned = True

        # Mass-spawn warriors early, using pairs of idle farmers.
        free_farmers = [c for c in farmers if c not in used]
        while step < self.SPAWN_WARRIOR_UNTIL \
                and len(free_farmers) >= 2 \
                and available >= self.WARRIOR_COST + self.RESERVE:
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