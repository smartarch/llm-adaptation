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

        # ---- 1. Meals are the top priority (survival + meal-timing rule) ----
        # Anyone at 5+ steps must eat now, or they starve next step.
        for c in sorted(comps, key=lambda x: -x.steps_since_meal):
            if c not in assigned and c.steps_since_meal >= 5 and wheat > 0:
                assigned[c] = "eat"
                wheat -= 1
        # Warriors may not be sent to the Cave at 3+ steps since a meal.
        for w in sorted(warriors, key=lambda x: -x.steps_since_meal):
            if w not in assigned and w.steps_since_meal >= 3 and wheat > 0:
                assigned[w] = "eat"
                wheat -= 1
        # Farmers eat proactively only when wheat is comfortable.
        if wheat >= 16:
            for f in sorted(farmers, key=lambda x: -x.steps_since_meal):
                if f not in assigned and f.steps_since_meal >= 4 and wheat > 0:
                    assigned[f] = "eat"
                    wheat -= 1

        avail = sorted(
            [f for f in farmers if f not in assigned],
            key=lambda x: x.steps_since_meal,
        )

        # ---- 2. Spawn plan: maximize warrior throughput ----
        # Spawners survive, so more pairs = more villagers. We only reserve
        # enough farmers to keep producing wheat (and to satisfy spawn >= 2).
        if n_farmers >= 3:
            farming_reserve = 1 if wheat >= 20 else 2
        else:
            farming_reserve = 0  # too small not to grow
        farming_reserve = min(farming_reserve, max(0, len(avail)))

        max_pairs = max(0, (len(avail) - farming_reserve)) // 2

        # Scale pairs-per-step with the wheat bank: never sit on idle wheat.
        if wheat >= 40:
            pairs_allowed = 4
        elif wheat >= 28:
            pairs_allowed = 3
        elif wheat >= 18:
            pairs_allowed = 2
        else:
            pairs_allowed = 1

        idx = 0
        pairs_done = 0
        added_farmers = 0
        while pairs_done < max_pairs and pairs_done < pairs_allowed:
            # Build a tiny farmer base first, with at least 2 guaranteed farmers
            # and 2 warriors overall to satisfy the "a few of each" requirement.
            want_farmer = (
                (n_farmers + added_farmers) < 3
                or (self.spawned_farmers < 2 and (n_farmers + added_farmers) < 4)
            )
            if want_farmer and wheat >= 10:
                grp, cost = "spawn farmer", 10
                added_farmers += 1
                self.spawned_farmers += 1
            elif wheat >= 12:
                grp, cost = "spawn warrior", 12
                self.spawned_warriors += 1
            else:
                break

            assigned[avail[idx]] = grp
            assigned[avail[idx + 1]] = grp
            idx += 2
            wheat -= cost
            pairs_done += 1

        # Remaining farmers farm.
        for f in avail[idx:]:
            assigned[f] = "farm"

        # ---- 3. Warriors in the Village ----
        # Fresh warriors head straight to the Cave so they begin attacking.
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
        dragon_hp = int(getattr(environment.dragon, "hp", 999))
        cave_warriors = [
            c for c in components if c.role == "Warrior" and c.hp > 0
        ]

        for c in components:
            if c.role != "Warrior" or c.hp <= 0:
                # Non-warriors / dead: travel home.
                environment.assign_group(c, "village")
                continue

            can_attack = c.steps_since_meal <= 5  # starving at 6 => no damage

            if not can_attack:
                environment.assign_group(c, "village")
                continue

            # Endgame all-in: if the current attackers can already finish the
            # Dragon before anyone would need to leave, keep everyone attacking.
            finishing = dragon_hp <= 3 * len(cave_warriors)
            if finishing:
                environment.assign_group(c, "attack")
                continue

            # Otherwise, pull a warrior home to eat *before* it starves:
            # leave the Cave at 4+ steps so the meal lands by step 5 (no starvation).
            if c.steps_since_meal >= 4:
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")