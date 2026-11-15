Strategy summary:
- Treat meal management as the highest priority: anyone at 5+ steps without food eats immediately if wheat is available; warriors at 3+ steps eat before going to the Cave.
- Farmers remain in the Village and either farm, eat, or join a spawn group. Spawning is balanced, with early priority for warriors so the first Dragon attack can happen within 15 steps.
- Cave warriors attack by default. Warriors are rotated back to the Village before they become too hungry, with staggered meal timing to keep at least one warrior attacking almost every step.
- A stateful tracker records whether the Dragon has been attacked yet and when the last attack happened, so the adaptation can avoid long no-attack gaps.
- Spawn attempts target two new farmers and two new warriors.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._first_observed_step = None
        self._seen_ids = set()

        self.warrior_ever = False
        self.first_attack_step = None
        self.last_attack_step = None
        self.last_attacker_count = 0

        self.target_farmers = 2
        self.target_warriors = 2
        self.spawn_attempts_farmers = 0
        self.spawn_attempts_warriors = 0

    def _register(self, components, step):
        if self._first_observed_step is None:
            self._first_observed_step = step

        for c in components:
            cid = id(c)
            if cid not in self._seen_ids:
                self._seen_ids.add(cid)
                if getattr(c, "role", None) == "Warrior":
                    self.warrior_ever = True

    def assign_in_village(self, components, environment, group_ids, step: int):
        comps = list(components)
        self._register(comps, step)

        assigned = {}
        wheat_left = max(0, int(getattr(environment.farm, "wheat", 0)))

        # 1. Emergency meals: anyone at 5+ steps must eat if possible.
        for c in sorted(comps, key=lambda x: x.steps_since_meal, reverse=True):
            if c.steps_since_meal >= 5 and wheat_left > 0:
                assigned[c] = "eat"
                wheat_left -= 1

        # 2. Warriors that are too hungry to leave for the Cave eat first.
        for c in sorted(comps, key=lambda x: x.steps_since_meal, reverse=True):
            if c in assigned:
                continue
            if c.role == "Warrior" and c.steps_since_meal >= 3 and wheat_left > 0:
                assigned[c] = "eat"
                wheat_left -= 1

        # 3. Spawn planning. Prefer warriors early or when no warrior has been seen.
        need_f = self.spawn_attempts_farmers < self.target_farmers
        need_w = self.spawn_attempts_warriors < self.target_warriors

        if need_f or need_w:
            choose = None

            if need_w and (
                not self.warrior_ever
                or self.spawn_attempts_warriors <= self.spawn_attempts_farmers
            ):
                choose = "warrior"
            elif need_f:
                choose = "farmer"
            elif need_w:
                choose = "warrior"

            cost = 12 if choose == "warrior" else 10

            if choose is not None and wheat_left < cost:
                if choose == "warrior" and self.warrior_ever and need_f and wheat_left >= 10:
                    choose = "farmer"
                    cost = 10
                elif choose == "farmer" and need_w and wheat_left >= 12:
                    choose = "warrior"
                    cost = 12

            can_spawn = (
                choose is not None
                and ((choose == "warrior" and need_w) or (choose == "farmer" and need_f))
                and wheat_left >= cost
            )

            if can_spawn:
                # Prefer non-hungry farmers as spawners.
                pool = [
                    c for c in comps
                    if c not in assigned
                    and c.role == "Farmer"
                    and c.steps_since_meal < 5
                ]
                pool.sort(key=lambda x: x.steps_since_meal)
                spawners = pool[:2]

                # If there are not enough farmers, use low-hunger villagers.
                if len(spawners) < 2:
                    extra = [
                        c for c in comps
                        if c not in assigned
                        and c not in spawners
                        and c.steps_since_meal < 3
                    ]
                    extra.sort(
                        key=lambda x: (
                            0 if x.role == "Farmer" else 1,
                            x.steps_since_meal,
                        )
                    )
                    spawners += extra[:2 - len(spawners)]

                if len(spawners) >= 2:
                    grp = "spawn warrior" if choose == "warrior" else "spawn farmer"
                    for c in spawners[:2]:
                        assigned[c] = grp

                    wheat_left -= cost

                    if choose == "warrior":
                        self.spawn_attempts_warriors += 1
                    else:
                        self.spawn_attempts_farmers += 1

        # 4. Other villagers can eat proactively if wheat remains.
        for c in sorted(comps, key=lambda x: x.steps_since_meal, reverse=True):
            if c in assigned:
                continue
            if c.steps_since_meal >= 4 and wheat_left > 0:
                assigned[c] = "eat"
                wheat_left -= 1

        # 5. Defaults.
        for c in comps:
            if c in assigned:
                continue

            if c.role == "Farmer":
                assigned[c] = "farm"
            else:
                # Hungry warriors must not be sent to the Cave.
                if c.steps_since_meal >= 3:
                    assigned[c] = "farm"
                else:
                    assigned[c] = "cave"

        for c in comps:
            environment.assign_group(c, assigned[c])

    def assign_in_cave(self, components, environment, group_ids, step: int):
        comps = list(components)
        self._register(comps, step)

        assigned = {}
        warriors = []

        for c in comps:
            if c.role == "Warrior":
                warriors.append(c)
            else:
                assigned[c] = "village"

        if not warriors:
            for c in comps:
                if c not in assigned:
                    assigned[c] = "village"
            for c in comps:
                environment.assign_group(c, assigned[c])
            self.last_attacker_count = 0
            return

        n = len(warriors)
        leave_ids = set()

        if n == 1:
            w = warriors[0]

            if self.first_attack_step is None:
                # Get an early first hit if this warrior is not yet starving.
                if w.steps_since_meal < 5:
                    assigned[w] = "attack"
                else:
                    assigned[w] = "village"
            else:
                # With one warrior there is an unavoidable attack gap around meals.
                if w.steps_since_meal >= 4:
                    assigned[w] = "village"
                else:
                    assigned[w] = "attack"

        else:
            # Warriors at 4+ steps must return to eat.
            for w in warriors:
                if w.steps_since_meal >= 4:
                    leave_ids.add(id(w))

            # Keep at least one warrior in the Cave if possible.
            if len(leave_ids) == n:
                keep = min(warriors, key=lambda w: (w.steps_since_meal, -w.hp))
                leave_ids.discard(id(keep))

            staying = [w for w in warriors if id(w) not in leave_ids]

            # Do not voluntarily reduce the Cave force if the Dragon is at risk
            # of regenerating.
            risk = (
                self.last_attack_step is not None
                and (step - self.last_attack_step) >= 2
            )

            # Stagger meals among warriors that would otherwise leave together.
            if self.first_attack_step is not None and not risk and len(staying) >= 2:
                ages = [w.steps_since_meal for w in staying]

                if max(ages) >= 1 and len(set(ages)) == 1 and max(ages) <= 3:
                    eater = max(staying, key=lambda w: (w.hp, w.steps_since_meal))
                    leave_ids.add(id(eater))
                    staying.remove(eater)

                elif max(ages) >= 3:
                    oldest = max(staying, key=lambda w: w.steps_since_meal)
                    if any(
                        id(w) != id(oldest) and w.steps_since_meal <= 2
                        for w in staying
                    ):
                        leave_ids.add(id(oldest))
                        staying.remove(oldest)

            staying = [w for w in warriors if id(w) not in leave_ids]

            if not staying:
                keep = min(warriors, key=lambda w: (w.steps_since_meal, -w.hp))
                leave_ids.discard(id(keep))

            for w in warriors:
                assigned[w] = "village" if id(w) in leave_ids else "attack"

        attackers = [c for c in comps if assigned.get(c) == "attack"]

        if attackers:
            if self.first_attack_step is None:
                self.first_attack_step = step
            self.last_attack_step = step
            self.last_attacker_count = len(attackers)
        else:
            self.last_attacker_count = 0

        for c in comps:
            environment.assign_group(c, assigned[c])
```