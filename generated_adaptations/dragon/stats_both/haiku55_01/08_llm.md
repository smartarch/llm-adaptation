## Diagnosis of the last run

The win rate fell to 33% from 100%, and the Dragon was left unattacked for 4 steps. Three causes stand out:

1. **Warriors were lost in the Cave.** The Dragon killed 4.7 villagers on average. Its area attack (40%) hits every villager in the Cave, and warriors have only 6 HP. A warrior that stays in the Cave for many steps is steadily worn down, and the 20% "eat" attack removes one at random.
2. **Warriors stayed too long before returning.** With a return threshold of 4, warriors sometimes reached the 6-step starvation limit on the way home. That left the Dragon unattacked.
3. **Idle steps at the start.** Warriors that were just spawned or had just eaten sometimes waited in the Village, so attack pressure built up slowly.

## Revised strategy: Shorter cave stints and earlier relief

- **Return earlier:** Warriors leave the Cave once `steps_since_meal >= 3`. That leaves a safe margin for the walk back and the meal, so starvation is avoided, and it limits the time each warrior spends under the Dragon's area attacks.
- **Eat at 2 steps in the Village:** Hungry warriors eat right away and go straight back to the Cave the same step if they are not yet hungry again. Warriors that have just eaten (`steps_since_meal < 2`) go to the Cave without delay.
- **Keep warrior spawning going until step 16:** Spawning is limited by wheat, with a reserve equal to the number of meals due next step. This keeps the attacker count rising while still leaving time for fresh warriors to attack.
- **One farmer spawn early:** Still satisfies the farmer requirement, now using a reserve for meals as well.
- **Farmers never enter the Cave** and keep producing wheat.

The aim is a steadier attack force: more warriors in the Cave on most steps, fewer losses to area attacks, and no unattacked steps caused by starvation trips.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Steady-pressure strategy:
      - Warriors leave the Cave once they are 3 steps hungry, so they always
        have time to walk back (1 step) and eat before starving (6 steps).
      - Villagers in the Village eat when 2+ steps hungry, then warriors return
        to the Cave immediately.
      - Idle farmer pairs spawn warriors while wheat covers the cost plus the
        meals due next step (until SPAWN_WARRIOR_UNTIL).
      - One farmer spawn early to satisfy the farmer requirement.
      - Farmers farm in the Village and never enter the Cave.
    """

    EAT_THRESHOLD = 2          # village: eat when this many steps have passed
    RETURN_THRESHOLD = 3       # cave: go back to village when this hungry
    SPAWN_WARRIOR_UNTIL = 16   # later warriors would have too little time to attack
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

        # Reserve wheat for the meals of the eaters this step.
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
            else:
                environment.assign_group(c, "attack")
```