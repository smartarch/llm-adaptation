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

        # 1) Emergency meals: 5+ steps must eat.
        for c in sorted(comps, key=lambda x: -x.steps_since_meal):
            if c not in assigned and c.steps_since_meal >= 5 and free_wheat > 0:
                assigned[c] = "eat"
                free_wheat -= 1

        # 2) Warriors must eat at 3+ before going to the Cave.
        for w in sorted(warriors, key=lambda x: -x.steps_since_meal):
            if w not in assigned and w.steps_since_meal >= 3 and free_wheat > 0:
                assigned[w] = "eat"
                free_wheat -= 1

        # 3) Farmers eat proactively at 4+.
        for f in sorted(farmers, key=lambda x: -x.steps_since_meal):
            if f not in assigned and f.steps_since_meal >= 4 and free_wheat > 0:
                assigned[f] = "eat"
                free_wheat -= 1

        avail = sorted(
            [f for f in farmers if f not in assigned],
            key=lambda x: x.steps_since_meal,
        )

        # ---- Spawn planning ----
        # Allow using ALL free farmers when the colony is tiny (<=2), otherwise
        # protect at least one farming farmer so wheat income continues.
        max_pairs = len(avail) // 2
        if n_farmers > 2:
            max_pairs = min(max_pairs, max(0, (n_farmers - 1) // 2))

        bursts = 2 if free_wheat >= 24 else 1  # front-load attackers when rich
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

        # Remaining warriors: fresh ones head to the Cave immediately.
        for w in warriors:
            if w in assigned:
                continue
            assigned[w] = "cave" if (w.steps_since_meal < 3 and w.hp > 0) else "farm"

        for c in comps:
            if c not in assigned:
                assigned[c] = "farm" if c.role == "Farmer" else "cave"
            environment.assign_group(c, assigned[c])

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            # Attack for the whole damage-dealing window (starving starts at 6).
            if c.role == "Warrior" and c.hp > 0 and c.steps_since_meal <= 5:
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")