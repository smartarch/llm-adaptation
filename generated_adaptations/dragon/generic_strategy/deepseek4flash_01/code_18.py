from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.any_warrior_seen = False
        self.started_attack = False
        self.last_attackers = 0
        self.cave_warriors = 0
        self.farmer_rush = False

    # ------------------------------------------------------------------
    # Village
    # ------------------------------------------------------------------
    def assign_in_village(self, components, environment, group_ids, step: int):
        decisions = {}
        wheat = environment.farm.wheat
        dragon_hp = environment.dragon.hp

        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        if warriors:
            self.any_warrior_seen = True

        # Meals first.  Starvation protection has priority over spawning.
        def meal_priority(c):
            if c.steps_since_meal >= 6:
                return 200 + c.steps_since_meal
            if c.role == "Warrior":
                if c.steps_since_meal >= 5:
                    return 150 + c.steps_since_meal
                if c.steps_since_meal >= 4:
                    return 60 + c.steps_since_meal
            else:
                if c.steps_since_meal >= 5:
                    return 100 + c.steps_since_meal
            return 0

        meal_candidates = sorted(
            components,
            key=lambda c: (meal_priority(c), c.steps_since_meal),
            reverse=True,
        )

        for c in meal_candidates:
            if wheat <= 0:
                break
            if meal_priority(c) > 0:
                decisions[id(c)] = "eat"
                wheat -= 1

        available_farmers = [c for c in farmers if id(c) not in decisions]
        available_warriors = [c for c in warriors if id(c) not in decisions]

        def spawn_pair(target):
            nonlocal wheat
            if len(available_farmers) < 2:
                return False

            cost = 12 if target == "spawn warrior" else 10
            if wheat < cost:
                return False

            # Spawn the least hungry villagers so hungry ones can still eat/farm.
            available_farmers.sort(key=lambda c: c.steps_since_meal)
            pair = available_farmers[:2]
            for c in pair:
                available_farmers.remove(c)
                decisions[id(c)] = target

            wheat -= cost

            if target == "spawn warrior":
                self.any_warrior_seen = True
            return True

        # First warrior as early as possible.  Do not spawn an extra farmer
        # before the first warrior; that only delays the first Cave trip.
        if not self.any_warrior_seen and not warriors:
            if wheat >= 12 and len(available_farmers) >= 2:
                spawn_pair("spawn warrior")
        else:
            # Grow to six farmers in the opening.  Keep at least two farmers
            # working this step whenever possible.
            if (
                step <= 4
                and len(farmers) < 6
                and len(available_farmers) >= 4
                and wheat >= 10
            ):
                spawn_pair("spawn farmer")

        # Endgame: if the Dragon is close to death, spare farmers are more
        # useful as one-step-away attackers than as additional warriors that
        # need extra travel time.  Do this before spending wheat on spawning.
        if (
            self.started_attack
            and dragon_hp <= 12
            and step >= 8
            and available_farmers
        ):
            self.farmer_rush = True
            for c in available_farmers:
                decisions[id(c)] = "cave"
            available_farmers = []
        else:
            # Convert surplus wheat into warriors.  Normally keep two farmers
            # working; when the Dragon is already low or time is short, allow
            # a more aggressive spawn burst.
            aggressive = dragon_hp <= 28 or step >= 13

            if aggressive:
                max_pairs = len(available_farmers) // 2
            else:
                max_pairs = max(
                    1 if len(available_farmers) >= 2 else 0,
                    (len(available_farmers) - 2) // 2,
                )

            spawned_pairs = 0
            while (
                spawned_pairs < max_pairs
                and wheat >= 12
                and len(available_farmers) >= 2
            ):
                if not spawn_pair("spawn warrior"):
                    break
                spawned_pairs += 1

        # Warrior movement toward the Cave.
        if not self.started_attack:
            fresh = [
                c for c in available_warriors
                if c.steps_since_meal <= 3
            ]

            # Wait for a pair, unless a warrior is already waiting in the Cave.
            if self.cave_warriors >= 1:
                for c in available_warriors:
                    if c.steps_since_meal <= 3:
                        decisions[id(c)] = "cave"
                    else:
                        decisions[id(c)] = "farm"
            elif len(fresh) >= 2:
                for c in fresh:
                    decisions[id(c)] = "cave"
                for c in available_warriors:
                    if id(c) not in decisions:
                        decisions[id(c)] = "farm"
            else:
                for c in available_warriors:
                    decisions[id(c)] = "farm"
        else:
            # If the previous step had no attacker, allow one extra hunger
            # tick to restore coverage.
            hunger_limit = 4 if self.last_attackers == 0 else 3
            for c in available_warriors:
                if c.steps_since_meal <= hunger_limit:
                    decisions[id(c)] = "cave"
                else:
                    decisions[id(c)] = "farm"

        # Remaining farmers farm.
        for c in available_farmers:
            if id(c) not in decisions:
                decisions[id(c)] = "farm"

        # Safety fallback: every component must be assigned exactly once.
        for c in components:
            if id(c) not in decisions:
                if c.role == "Warrior":
                    if not self.started_attack:
                        decisions[id(c)] = "farm"
                    else:
                        decisions[id(c)] = (
                            "cave" if c.steps_since_meal <= 3 else "farm"
                        )
                else:
                    decisions[id(c)] = "farm"

        for c in components:
            environment.assign_group(c, decisions[id(c)])

    # ------------------------------------------------------------------
    # Cave
    # ------------------------------------------------------------------
    def assign_in_cave(self, components, environment, group_ids, step: int):
        decisions = {}

        warriors = [c for c in components if c.role == "Warrior"]
        others = [c for c in components if c.role != "Warrior"]

        if warriors:
            self.any_warrior_seen = True

        active = [
            w for w in warriors
            if w.steps_since_meal < 6
            and not (w.hp <= 1 and w.steps_since_meal >= 5)
        ]
        inactive_warriors = [w for w in warriors if w not in active]

        # Farmers are normally returned to the Village.  During the farmer
        # rush, usable farmers stay and attack.
        farmer_attackers = []
        for c in others:
            if (
                self.farmer_rush
                and self.started_attack
                and c.steps_since_meal < 6
                and c.hp > 0
            ):
                farmer_attackers.append(c)
            else:
                decisions[id(c)] = "village"

        if not self.started_attack:
            # Wait for a pair, or start if waiting would waste too much time
            # or a warrior is about to starve.
            can_start = False
            if len(active) >= 2:
                can_start = True
            elif step >= 10 and active:
                can_start = True
            elif step >= 6 and any(w.steps_since_meal >= 5 for w in active):
                can_start = True

            if can_start:
                for w in active:
                    decisions[id(w)] = "attack"
                for w in inactive_warriors:
                    decisions[id(w)] = "village"
                self.started_attack = True
            else:
                for w in active:
                    decisions[id(w)] = "cave"
                for w in inactive_warriors:
                    decisions[id(w)] = "village"

        else:
            # Attack with every warrior that can still deal damage.
            for w in active:
                decisions[id(w)] = "attack"
            for w in inactive_warriors:
                decisions[id(w)] = "village"

            # Farmer finishing attackers.
            for c in farmer_attackers:
                decisions[id(c)] = "attack"

            # If no warrior is attacking, keep one warrior as a regeneration
            # blocker even if it is currently too weak to deal damage.
            has_warrior_attacker = any(
                decisions.get(id(w)) == "attack" for w in warriors
            )

            if not has_warrior_attacker and not farmer_attackers:
                candidates = [w for w in warriors if w.hp > 0]
                if candidates:
                    blocker = min(
                        candidates,
                        key=lambda w: (w.steps_since_meal, -w.hp, id(w)),
                    )
                    decisions[id(blocker)] = "attack"

        # Safety fallback: every component must be assigned exactly once.
        for c in components:
            if id(c) not in decisions:
                decisions[id(c)] = "village"

        self.last_attackers = sum(
            1 for c in components
            if decisions[id(c)] == "attack"
        )
        self.cave_warriors = sum(
            1 for c in components
            if c.role == "Warrior" and decisions[id(c)] != "village"
        )

        for c in components:
            environment.assign_group(c, decisions[id(c)])