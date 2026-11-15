from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.spawned_farmers = 0
        self.spawned_warriors = 0

    def assign_in_village(self, components, environment, group_ids, step: int):
        comps = list(components)
        wheat = int(getattr(environment.farm, "wheat", 0))
        assigned = {}
        free_wheat = wheat

        farmers = [c for c in comps if c.role == "Farmer"]
        warriors = [c for c in comps if c.role == "Warrior"]
        n_farmers = len(farmers)

        # 1) Emergency meals: anyone at 5+ steps must eat now if possible.
        for c in sorted(comps, key=lambda x: x.steps_since_meal, reverse=True):
            if c.steps_since_meal >= 5 and free_wheat > 0:
                assigned[c] = "eat"
                free_wheat -= 1

        # 2) Warriors that would have to return before attacking should eat first.
        for w in sorted(warriors, key=lambda x: x.steps_since_meal, reverse=True):
            if w in assigned:
                continue
            if w.steps_since_meal >= 3 and free_wheat > 0:
                assigned[w] = "eat"
                free_wheat -= 1

        # 3) Farmers eat proactively to stay safe.
        for f in sorted(farmers, key=lambda x: x.steps_since_meal, reverse=True):
            if f in assigned:
                continue
            if f.steps_since_meal >= 4 and free_wheat > 0:
                assigned[f] = "eat"
                free_wheat -= 1

        # --- Spawn decision ---------------------------------------------------
        avail = [f for f in farmers if f not in assigned]
        avail.sort(key=lambda x: x.steps_since_meal)

        # Keep at least one farmer farming when possible.
        can_spawn = (
            len(avail) >= 3
            or (n_farmers <= 2 and len(avail) >= 2 and free_wheat >= 20)
        )

        want_farmer = (self.spawned_farmers < 2) and (n_farmers < 5)
        want_warrior = True

        if can_spawn and len(avail) >= 2:
            if want_farmer and free_wheat >= 10:
                grp, cost = "spawn farmer", 10
            elif want_warrior and free_wheat >= 12:
                grp, cost = "spawn warrior", 12
            else:
                grp, cost = None, 0

            if grp is not None:
                spawners = avail[:2]
                for c in spawners:
                    assigned[c] = grp
                free_wheat -= cost
                if grp == "spawn farmer":
                    self.spawned_farmers += 1
                else:
                    self.spawned_warriors += 1
                avail = avail[2:]

        # Remaining farmers farm.
        for f in avail:
            assigned[f] = "farm"

        # Remaining warriors: go to the Cave if fresh enough, otherwise eat/farm.
        for w in warriors:
            if w in assigned:
                continue
            if w.steps_since_meal < 3:
                assigned[w] = "cave"
            else:
                assigned[w] = "farm"

        # Safety net for any leftover component.
        for c in comps:
            if c not in assigned:
                assigned[c] = "farm" if c.role == "Farmer" else "cave"
            environment.assign_group(c, assigned[c])

    def assign_in_cave(self, components, environment, group_ids, step: int):
        comps = list(components)
        assigned = {}

        for c in comps:
            if c.role != "Warrior":
                # Non-warriors should not be fighting; send them home.
                assigned[c] = "village"
                continue

            # Attack as long as we still deal damage (starving only starts at 6).
            # Otherwise travel back so we can eat in the Village.
            if c.steps_since_meal <= 5 and c.hp > 0:
                assigned[c] = "attack"
            else:
                assigned[c] = "village"

        for c in comps:
            environment.assign_group(c, assigned[c])