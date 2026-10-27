The 20.0 run regressed because I raised the farmer target to 3–5, which spent wheat and turns on farmers instead of getting attackers into the Cave. The 18.7 version's economy was already near the sweet spot: wheat income is the real limiter (each warrior costs 12 wheat, and a spawn pair itself consumes two farmers' turns, so sustaining a warrior stream needs a large farm base). The best way to shave turns is **not** to build a bigger farm base, but to:
- keep the proven one-pair stream / modest burst model,
- conserve wheat by not over-feeding farmers when it competes with warrior spawns,
- and front-load warriors slightly more aggressively when wheat is banked.

I revert to the 18.7 core and make three small, honest tunings: (1) farmers eat proactively only when wheat is comfortable, otherwise only at the starvation edge; (2) the burst threshold is raised to 26 so bursts don't drain the meal/spawn reserve; (3) at 3+ farmers, we keep only one farmer farming to free an extra spawn pair.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.spawned_farmers = 0
        self.spawned_warriors = 0

    def assign_in_village(self, components, environment, group_ids, step: int):
        comps = list(components)
        free_wheat = max(0, int(getattr(environment.farm, "wheat", 0)))
        wheat_start = free_wheat
        assigned = {}

        farmers = [c for c in comps if c.role == "Farmer"]
        warriors = [c for c in comps if c.role == "Warrior"]
        n_farmers = len(farmers)

        # ---- 1. Emergency meals: 5+ steps must eat (no starvation) ----
        for c in sorted(comps, key=lambda x: -x.steps_since_meal):
            if c not in assigned and c.steps_since_meal >= 5 and free_wheat > 0:
                assigned[c] = "eat"
                free_wheat -= 1

        # ---- 2. Warriors must eat at 3+ before going to the Cave ----
        for w in sorted(warriors, key=lambda x: -x.steps_since_meal):
            if w not in assigned and w.steps_since_meal >= 3 and free_wheat > 0:
                assigned[w] = "eat"
                free_wheat -= 1

        # ---- 3. Farmers eat proactively only when wheat is comfortable,
        #         so we do not steal wheat from the warrior stream. ----
        if wheat_start >= 15:
            for f in sorted(farmers, key=lambda x: -x.steps_since_meal):
                if f not in assigned and f.steps_since_meal >= 4 and free_wheat > 0:
                    assigned[f] = "eat"
                    free_wheat -= 1

        avail = sorted(
            [f for f in farmers if f not in assigned],
            key=lambda x: x.steps_since_meal,
        )

        # ---- 4. Spawn plan ----
        # With <=2 farmers, use them all (otherwise growth deadlocks).
        # With 3+ farmers, keep exactly one farming to sustain wheat income.
        if n_farmers <= 2:
            max_pairs = len(avail) // 2
        else:
            max_pairs = max(0, (len(avail) - 1) // 2)

        bursts = 2 if free_wheat >= 26 else 1
        want_farmer = self.spawned_farmers < 2 and n_farmers < 4

        idx = 0
        done = 0
        while done < max_pairs and done < bursts:
            if want_farmer and free_wheat >= 10:
                grp, cost = "spawn farmer", 10
                want_farmer = False
            elif free_wheat >= 12:
                grp, cost = "spawn warrior", 12
            else:
                break

            assigned[avail[idx]] = grp
            assigned[avail[idx + 1]] = grp
            idx += 2
            free_wheat -= cost
            done += 1

            if grp == "spawn farmer":
                self.spawned_farmers += 1
            else:
                self.spawned_warriors += 1

        # Remaining farmers farm.
        for f in avail[idx:]:
            assigned[f] = "farm"

        # Remaining warriors: fresh ones head straight to the Cave.
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
            # Attack for the full damage-dealing window (starving starts at 6);
            # otherwise travel home so the villager can eat.
            if c.role == "Warrior" and c.hp > 0 and c.steps_since_meal <= 5:
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```