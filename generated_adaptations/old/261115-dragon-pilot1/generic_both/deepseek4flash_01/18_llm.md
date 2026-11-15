We've plateaued because the 18.7 version was already near-maximally aggressive: warriors attack on *every* step they're able (starving only at 6), so there's no "optional" leaving to reclaim. The regressions came from (a) building too many farmers early and (b) recalling warriors at 4 steps instead of letting them use the full damage window. The clear lesson: **attack while `steps_since_meal ≤ 5`** and **don't expand the farm base beyond what's needed**.

The only remaining lever is converting banked wheat into attackers *sooner*. I restore the 18.7 core and make the burst count scale with the wheat bank (1 → 2 → 3 pairs), so idle wheat becomes early warriors instead of sitting unused.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.spawned_farmers = 0
        self.spawned_warriors = 0

    def assign_in_village(self, components, environment, group_ids, step: int):
        comps = list(components)
        wheat = max(0, int(getattr(environment.farm, "wheat", 0)))
        assigned = {}

        farmers = [c for c in comps if c.role == "Farmer"]
        warriors = [c for c in comps if c.role == "Warrior"]
        n_farmers = len(farmers)

        # ---- 1. Meals (top priority) ----
        # Emergency: anyone at 5+ steps eats now.
        for c in sorted(comps, key=lambda x: -x.steps_since_meal):
            if c not in assigned and c.steps_since_meal >= 5 and wheat > 0:
                assigned[c] = "eat"
                wheat -= 1
        # Warriors must eat at 3+ before heading to the Cave.
        for w in sorted(warriors, key=lambda x: -x.steps_since_meal):
            if w not in assigned and w.steps_since_meal >= 3 and wheat > 0:
                assigned[w] = "eat"
                wheat -= 1
        # Farmers eat proactively at 4+.
        for f in sorted(farmers, key=lambda x: -x.steps_since_meal):
            if f not in assigned and f.steps_since_meal >= 4 and wheat > 0:
                assigned[f] = "eat"
                wheat -= 1

        avail = sorted(
            [f for f in farmers if f not in assigned],
            key=lambda x: x.steps_since_meal,
        )

        # ---- 2. Spawn: get warriors out fast, use all spare pairs ----
        # Keep >=1 farmer farming once the colony is big enough to afford it.
        if n_farmers <= 2:
            max_pairs = len(avail) // 2
        else:
            max_pairs = max(0, len(avail) - 1) // 2

        # Convert banked wheat into earlier attackers (never sit on idle wheat).
        if wheat >= 36:
            pairs_allowed = 3
        elif wheat >= 22:
            pairs_allowed = 2
        else:
            pairs_allowed = 1

        idx = 0
        done = 0
        added_farmers = 0
        while done < max_pairs and done < pairs_allowed:
            want_farmer = (
                self.spawned_farmers < 2
                and (n_farmers + added_farmers) < 4
            )
            if want_farmer and wheat >= 10:
                grp, cost = "spawn farmer", 10
                self.spawned_farmers += 1
                added_farmers += 1
            elif wheat >= 12:
                grp, cost = "spawn warrior", 12
                self.spawned_warriors += 1
            else:
                break

            assigned[avail[idx]] = grp
            assigned[avail[idx + 1]] = grp
            idx += 2
            wheat -= cost
            done += 1

        # Remaining farmers farm.
        for f in avail[idx:]:
            assigned[f] = "farm"

        # ---- 3. Village warriors: fresh ones go straight to the Cave ----
        for w in warriors:
            if w in assigned:
                continue
            assigned[w] = "cave" if (w.steps_since_meal < 3 and w.hp > 0) else "farm"

        # Safety net + apply.
        for c in comps:
            if c not in assigned:
                assigned[c] = "farm" if c.role == "Farmer" else "cave"
            environment.assign_group(c, assigned[c])

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            # Attack for the full window in which damage is dealt
            # (starvation / no-damage begins only at steps_since_meal >= 6).
            # Otherwise travel home so the villager can eat.
            if c.role == "Warrior" and c.hp > 0 and c.steps_since_meal <= 5:
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```