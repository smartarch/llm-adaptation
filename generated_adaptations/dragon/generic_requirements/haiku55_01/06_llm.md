## Revised strategy: Fewer wasted meals and longer cave stays

The 33% win rate suggests the damage output is still too low. In the last version, warriors ate every step in the village, which wasted wheat that could have funded spawns. They also returned from the cave after only about 2 attack steps. The changes below target both problems.

**Changes:**

1. **Economical eating in the village.** Warriors eat only when `steps_since_meal >= 2`. Eating every step burned wheat for no benefit. A warrior that ate recently can leave for the cave right away.
2. **Longer cave stays.** Warriors return home only at `steps_since_meal >= 4`. That still leaves two steps of margin before the 6-step starvation limit, since the trip home takes one step. More attack steps per trip means more damage per warrior and fewer steps without attacks. Any step with an attack also prevents the Dragon's 5 HP regeneration.
3. **Early farmer spawn for wheat income.** A farmer produces 5 wheat per step, far more than a warrior. One farmer spawn is issued early (while steps are still small and wheat is available) to build the economy before warrior spawns use it.
4. **Warrior spawns from all remaining farmer pairs.** Wheat limits how many are issued, and the cap is loose.
5. **Farmers never enter the cave**, so they keep their HP and keep producing wheat.

These thresholds are still heuristic and untested against the simulator. The main levers are `EAT_IN_VILLAGE_MIN`, `RETURN_THRESHOLD`, and the early farmer spawn rule.

```py
import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Economical warrior rotation:
      - Warriors eat in the village only when they have gone 2+ steps without a meal,
        which saves wheat compared to eating every step.
      - Warriors that recently ate go to the cave and attack.
      - In the cave, warriors stay while fed and return home at 4 unmet steps,
        leaving 2 steps of margin before starvation (travel takes one step).
      - One farmer spawn is issued early to grow the wheat economy,
        then remaining farmer pairs are turned into warriors while wheat allows.
    """

    EAT_IN_VILLAGE_MIN = 2   # village warriors eat once this many steps have passed
    RETURN_THRESHOLD = 4     # cave warriors go home at this many unmet steps
    EARLY_FARMER_STEP = 6    # farmer spawn is prioritised before this step
    MAX_WARRIOR_SPAWNS = 8
    MAX_FARMER_SPAWNS = 1

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.warrior_spawn_orders = 0
        self.farmer_spawn_orders = 0

    def assign_in_village(self, components, environment, group_ids, step: int):
        budget = environment.farm.wheat

        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role != "Warrior"]

        # 1. Warriors that have gone without a meal for a while eat first.
        eaters = []
        ready_warriors = []
        for w in warriors:
            if w.steps_since_meal >= self.EAT_IN_VILLAGE_MIN and budget >= 1:
                eaters.append(w)
                budget -= 1
            else:
                ready_warriors.append(w)

        available = list(farmers)

        # 2. Early farmer spawn to grow wheat income.
        spawn_farmer = []
        if (step <= self.EARLY_FARMER_STEP and len(available) >= 2 and budget >= 10
                and self.farmer_spawn_orders < self.MAX_FARMER_SPAWNS):
            spawn_farmer.extend(available[:2])
            available = available[2:]
            budget -= 10
            self.farmer_spawn_orders += 1

        # 3. Pair remaining farmers into warrior spawns while wheat allows.
        spawn_warrior = []
        while (len(available) >= 2 and budget >= 12
               and self.warrior_spawn_orders < self.MAX_WARRIOR_SPAWNS):
            spawn_warrior.extend(available[:2])
            available = available[2:]
            budget -= 12
            self.warrior_spawn_orders += 1

        # 4. Late farmer spawn if affordable and not yet done.
        if (len(available) >= 2 and budget >= 10
                and self.farmer_spawn_orders < self.MAX_FARMER_SPAWNS):
            spawn_farmer.extend(available[:2])
            available = available[2:]
            budget -= 10
            self.farmer_spawn_orders += 1

        # 5. Assign everyone exactly once.
        for c in eaters:
            environment.assign_group(c, "eat")
        for c in spawn_warrior:
            environment.assign_group(c, "spawn warrior")
        for c in spawn_farmer:
            environment.assign_group(c, "spawn farmer")
        for c in ready_warriors:
            environment.assign_group(c, "cave")
        for c in available:
            environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role != "Warrior"]

        # Farmers should not be here; send them back to produce wheat.
        for c in farmers:
            environment.assign_group(c, "village")

        # Warriors near starvation go home; the rest keep attacking.
        for w in warriors:
            if w.steps_since_meal >= self.RETURN_THRESHOLD:
                environment.assign_group(w, "village")
            else:
                environment.assign_group(w, "attack")
```