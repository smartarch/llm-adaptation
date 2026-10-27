We've oscillated 18.7 ↔ 20.0, and the pattern is clear: every attempt to "improve" by expanding the farm base or draining the wheat bank (bigger bursts) **regressed**, because it steals wheat that the meal-timing rules require and delays warriors reaching the Cave. The 18.7 run was the genuine sweet spot: a small, stable farmer base with a one-pair (occasionally two-pair) warrior stream, staggered by construction so somebody is almost always in the Cave attacking.

The honest improvement here is to **lock in that proven economy exactly** and keep the combat logic maximally greedy — attack on *every* step a warrior still deals damage (`steps_since_meal ≤ 5`), since recalling earlier only loses DPS and starvation damage does not begin until step 6. Any more-aggressive spawn schedule made it worse, so I'm deliberately *not* doing that.

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
        assigned = {}

        farmers = [c for c in comps if c.role == "Farmer"]
        warriors = [c for c in comps if c.role == "Warrior"]
        n_farmers = len(farmers)

        # ---- 1. Meals: highest priority (survival + warrior meal-timing rule) ----
        # Anyone at 5+ steps must eat now (starvation damage starts at 6).
        for c in sorted(comps, key=lambda x: -x.steps_since_meal):
            if c not in assigned and c.steps_since_meal >= 5 and free_wheat > 0:
                assigned[c] = "eat"
                free_wheat -= 1
        # A warrior may not be sent to the Cave at 3+ steps since its last meal.
        for w in sorted(warriors, key=lambda x: -x.steps_since_meal):
            if w not in assigned and w.steps_since_meal >= 3 and free_wheat > 0:
                assigned[w] = "eat"
                free_wheat -= 1
        # Farmers eat proactively at 4+ so they never reach the starvation edge.
        for f in sorted(farmers, key=lambda x: -x.steps_since_meal):
            if f not in assigned and f.steps_since_meal >= 4 and free_wheat > 0:
                assigned[f] = "eat"
                free_wheat -= 1

        avail = sorted(
            [f for f in farmers if f not in assigned],
            key=lambda x: x.steps_since_meal,
        )

        # ---- 2. Spawn plan (proven small-base + steady warrior stream) ----
        # When the colony is tiny, use all available pairs (otherwise growth
        # deadlocks). Once past 2 farmers, protect one farmer to sustain income.
        if n_farmers > 2:
            max_pairs = min(len(avail) // 2, max(0, (n_farmers - 1) // 2))
        else:
            max_pairs = len(avail) // 2

        # A single pair per step preserves the wheat/meal reserve; allow a second
        # pair only when wheat is genuinely banked (idle wheat is wasted damage).
        bursts = 2 if free_wheat >= 24 else 1
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

        # ---- 3. Village warriors: fresh ones head straight to the Cave ----
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
            # Attack for the full damage-dealing window: no-damage / starving
            # state only begins once steps_since_meal reaches 6. Recalling any
            # earlier would only sacrifice DPS. Otherwise travel home to eat.
            if c.role == "Warrior" and c.hp > 0 and c.steps_since_meal <= 5:
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```