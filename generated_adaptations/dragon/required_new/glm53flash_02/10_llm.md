**Analysis of the failures:** two problems. First, the "finisher" squeeze let warriors linger in the Cave at hunger 5 — next step they hit 6 and starve, violating the constraint. Second, the step-24 "all-in" sent farmers to the Cave, wheat production collapsed, and villagers starved with no food. Fixes:

1. **Hunger safety is now absolute:** recall from the Cave strictly at hunger ≥ 3, no exceptions; in the Village, eat at hunger ≥ 4 whenever wheat is available; if wheat is 0, farmers farm to restore food.
2. **Emergency all-in is conditional:** only farmers who don't need to eat soon (hunger ≤ 2, so they can return in time) join the assault, and only while there is a wheat reserve. Farmers otherwise keep farming.
3. **Assault economy:** keep spawning warrior pairs during the assault to replace losses, but always with a food reserve.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    EAT_AT = 4          # eat in village when this hungry
    LEAVE_CAVE_AT = 3   # leave cave when this hungry (arrive home at 4, eat)
    WARRIOR_CAP = 16

    def assign_in_village(self, components, environment, group_ids, step):
        wheat = environment.farm.wheat
        total_warriors = len(environment.warriors)
        total_villagers = total_warriors + len(environment.farmers)

        assault = total_warriors >= 5 or step >= 10
        emergency = step >= 24 and total_warriors > 0

        hungry_count = sum(1 for c in components if c.steps_since_meal >= self.EAT_AT)

        # ---- spawn planning (with food reserve) ----
        w_pairs = 0
        f_pairs = 0
        reserve = hungry_count + 6
        budget = wheat - reserve
        if not emergency:
            if step < 6 and total_villagers < 9:
                f_pairs = max(0, min(1, (budget - 14) // 10))
                budget -= f_pairs * 10
            if step < 20 and total_warriors < self.WARRIOR_CAP:
                w_pairs = max(0, budget // 12)

        w_left = w_pairs * 2
        f_left = f_pairs * 2

        for c in components:
            # 1) eating has top priority, always
            if c.steps_since_meal >= self.EAT_AT and wheat > 0:
                environment.assign_group(c, "eat")
                wheat -= 1
                continue

            # 2) spawn duties (complete pairs only)
            if w_left >= 2:
                environment.assign_group(c, "spawn warrior")
                w_left -= 1
                wheat -= 6
                continue
            if f_left >= 2:
                environment.assign_group(c, "spawn farmer")
                f_left -= 1
                wheat -= 5
                continue

            # 3) warriors: attack during assault
            if c.role == "Warrior":
                environment.assign_group(c, "cave" if (assault or emergency) else "farm")
                continue

            # 4) farmers: farm to feed the war; join late push only if safe
            if emergency and c.steps_since_meal <= 2 and wheat >= 6:
                environment.assign_group(c, "cave")
            else:
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        for c in components:
            # strict hunger safety: no exceptions, never risk starving in the Cave
            if c.steps_since_meal >= self.LEAVE_CAVE_AT:
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")
```