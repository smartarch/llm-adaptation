**Fixes:**

1. **Remove the "finisher" override** — it kept villagers in the Cave at hunger 4–5, causing both the "should go to the Village now" violations and, when it chained, actual starving (hunger 5 → 6). Cave recall is now strict: leave at hunger 4, no exceptions.
2. **Stronger food reserve:** the reserve now also counts villagers at hunger 4 who will need to eat next step, so spawning can't drain wheat right before a meal is due (this caused the step-12 starvation with `initial_wheat=15`).

The tight 5/7 attack cycle stays, which is what pushed the win rate to 67%.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    EAT_AT = 5          # eat in village when this hungry (starving starts at 6)
    LEAVE_CAVE_AT = 4   # leave cave at 4 -> arrive at 5 -> eat -> safe
    WARRIOR_CAP = 18

    def assign_in_village(self, components, environment, group_ids, step):
        wheat = environment.farm.wheat
        total_warriors = len(environment.warriors)
        total_villagers = total_warriors + len(environment.farmers)

        assault = total_warriors >= 4 or step >= 10
        late = step >= 20

        # everyone at hunger >= 4 will need to eat within the next 2 steps
        soon_hungry = sum(1 for c in components if c.steps_since_meal >= 4)

        # ---- spawn planning (with food reserve) ----
        reserve = soon_hungry + 4
        budget = max(0, wheat - reserve)
        f_pairs = 0
        w_pairs = 0
        if step < 5 and total_villagers < 10:
            f_pairs = max(0, min(2, (budget - 20) // 10))
            budget -= f_pairs * 10
        if total_warriors < self.WARRIOR_CAP:
            w_pairs = max(0, min(4, budget // 12))
            budget -= w_pairs * 12

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
                environment.assign_group(c, "cave" if (assault or late) else "farm")
                continue

            # 4) farmers: mostly farm; surplus joins the assault when rich
            if late and c.steps_since_meal <= 2 and wheat >= 8:
                environment.assign_group(c, "cave")
            elif assault and total_warriors >= 6 and wheat >= 40 and c.steps_since_meal <= 2:
                environment.assign_group(c, "cave")
            else:
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        for c in components:
            # strict safety: leave at hunger 4, arrive home at 5, eat — never hunger 6
            if c.steps_since_meal >= self.LEAVE_CAVE_AT:
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")
```