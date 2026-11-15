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

        # ---- 1. Meals: highest priority to avoid starvation ----
        for c in sorted(comps, key=lambda x: -x.steps_since_meal):
            if c in assigned:
                continue
            if c.steps_since_meal >= 5 and wheat > 0:
                assigned[c] = "eat"
                wheat -= 1
        # Warriors must eat at 3+ before being sent to the Cave.
        for w in sorted(warriors, key=lambda x: -x.steps_since_meal):
            if w not in assigned and w.steps_since_meal >= 3 and wheat > 0:
                assigned[w] = "eat"
                wheat -= 1
        # Farmers eat proactively.
        for f in sorted(farmers, key=lambda x: -x.steps_since_meal):
            if f not in assigned and f.steps_since_meal >= 4 and wheat > 0:
                assigned[f] = "eat"
                wheat -= 1

        avail = sorted(
            [f for f in farmers if f not in assigned],
            key=lambda x: x.steps_since_meal,
        )

        # ---- 2. Spawn plan ----
        # Grow a small farmer base fast, then feed a sustained warrior stream.
        # When wheat is rich, raise the farmer target and allow bigger bursts.
        target_farmers = 3
        if wheat >= 35:
            target_farmers = 5
        elif wheat >= 22:
            target_farmers = 4

        # Keep some farmers farming for income; allow more spawn pairs when rich.
        if wheat >= 40:
            keep_cap = 1
        elif wheat >= 20:
            keep_cap = 2
        else:
            keep_cap = 3

        keep = min(keep_cap, max(0, len(avail) - 2))
        max_pairs = max(0, (len(avail) - keep) // 2)

        idx = 0
        pairs_done = 0
        added_farmers = 0

        while pairs_done < max_pairs:
            if (n_farmers + added_farmers) < target_farmers and wheat >= 10:
                grp, cost = "spawn farmer", 10
            elif wheat >= 12:
                grp, cost = "spawn warrior", 12
            else:
                break

            assigned[avail[idx]] = grp
            assigned[avail[idx + 1]] = grp
            idx += 2
            wheat -= cost
            pairs_done += 1

            if grp == "spawn farmer":
                self.spawned_farmers += 1
                added_farmers += 1
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
            # Attack for the full window in which we still deal damage
            # (no-damage/starving begins only at steps_since_meal >= 6).
            # Otherwise travel home so the villager can eat.
            if c.role == "Warrior" and c.hp > 0 and c.steps_since_meal <= 5:
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")