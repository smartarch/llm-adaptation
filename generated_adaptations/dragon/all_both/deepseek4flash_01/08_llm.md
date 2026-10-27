The remaining failures are all coverage gaps, plus a starvation case caused by over‑spending wheat on spawns. Two things had to change fundamentally:

1. **Meals must never lose wheat to spawning.** Spawning now only happens when, after paying the cost, enough wheat remains for everyone who is close to needing a meal. That fixes the `step 6` starvation.
2. **Coverage needs *staggered* trips and enough warriors.** A meal round trip costs 3 non‑attacking steps, so if all warriors hit the "must eat" wall together the Dragon goes unattacked for 3+ steps. The cave logic now: attack while `steps_since_meal <= 3`, only return at `>= 4`, and *proactively* pull the hungriest attacker out when there are 3+ attackers so their trips never bunch up. Villagers eat at `>= 5` (mandatory) and warriors eat at `>= 3` before going back out, so they always re‑enter fresh.
3. **A continuous warrior pipeline.** Farmers farm, and whenever wheat allows (beyond the meal reserve) two farmers spawn another warrior. This keeps 3+ warriors available to rotate, which is what makes continuous coverage possible.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.first_attack_step = None
        self.last_attack_step = None
        self.spawned_warriors = 0
        self.spawned_farmers = 0

    # ------------------------------------------------------------------ #
    #  VILLAGE                                                            #
    # ------------------------------------------------------------------ #
    def assign_in_village(self, components, environment, group_ids, step: int):
        components = list(components)
        budget = int(environment.farm.wheat)
        eaten_ids = set()

        # 1) Mandatory eating: anyone at the starvation boundary eats now.
        for c in sorted(components, key=lambda x: x.steps_since_meal, reverse=True):
            if c.steps_since_meal >= 5 and budget > 0:
                environment.assign_group(c, "eat")
                eaten_ids.add(id(c))
                budget -= 1

        # 2) Warriors that would otherwise go back out already hungry eat
        #    first, so they can attack several steps before returning.
        for c in sorted(components, key=lambda x: x.steps_since_meal, reverse=True):
            if id(c) in eaten_ids or c.role != "Warrior":
                continue
            if c.steps_since_meal >= 3 and budget > 0:
                environment.assign_group(c, "eat")
                eaten_ids.add(id(c))
                budget -= 1

        remaining = [c for c in components if id(c) not in eaten_ids]
        warriors = [c for c in remaining if c.role == "Warrior"]
        farmers = [c for c in remaining if c.role == "Farmer"]

        # 3) Fresh warriors go to the Cave; hungry ones stay back to farm
        #    (they were normally just fed above).
        for w in warriors:
            if w.steps_since_meal <= 3:
                environment.assign_group(w, "cave")
            else:
                environment.assign_group(w, "farm")

        # 4) Wheat that must be kept for people about to need a meal.  Spawns
        #    are only allowed on top of this, so feeding can never fail.
        imminent = sum(
            1
            for c in components
            if c.steps_since_meal >= 4 and id(c) not in eaten_ids
        )
        reserve = imminent + 4

        # 5) Spawn pipeline.  First get a couple of warriors out for early
        #    damage, then a couple of farmers, then keep replenishing warriors.
        spawn_group = None
        spawners = []
        cands = sorted(farmers, key=lambda x: x.steps_since_meal)

        if len(cands) >= 2:
            want_warrior = (
                self.spawned_warriors < 2
                or (self.spawned_farmers >= 2 and self.spawned_warriors < 6)
                or self.spawned_farmers < 2 and self.spawned_warriors < 1
            )
            want_farmer = self.spawned_farmers < 2

            if want_warrior and budget - 12 >= reserve:
                spawn_group = "spawn warrior"
                spawners = cands[:2]
                budget -= 12
                self.spawned_warriors += 1
            elif want_farmer and budget - 10 >= reserve:
                spawn_group = "spawn farmer"
                spawners = cands[:2]
                budget -= 10
                self.spawned_farmers += 1

        spawner_ids = {id(c) for c in spawners}
        if spawn_group is not None:
            for c in spawners:
                environment.assign_group(c, spawn_group)

        # 6) Every other farmer stays in the Village to farm.
        for c in farmers:
            if id(c) not in spawner_ids:
                environment.assign_group(c, "farm")

    # ------------------------------------------------------------------ #
    #  CAVE                                                               #
    # ------------------------------------------------------------------ #
    def assign_in_cave(self, components, environment, group_ids, step: int):
        components = list(components)
        warriors = [c for c in components if c.role == "Warrior"]

        # Farmers have no business in the Cave.
        for c in components:
            if c.role != "Warrior":
                environment.assign_group(c, "village")

        if not warriors:
            return

        # Attacking is safe while steps_since_meal <= 3; at >= 4 a warrior
        # must head back to eat.
        attackers = [w for w in warriors if w.steps_since_meal <= 3]
        returners = [w for w in warriors if w.steps_since_meal >= 4]

        # Proactive staggering: when several warriors are attacking, pull the
        # hungriest one out early so the meal trips never bunch together,
        # which is what keeps the Dragon under fire continuously.
        if len(attackers) >= 3:
            hungriest = max(attackers, key=lambda w: w.steps_since_meal)
            if hungriest.steps_since_meal >= 3:
                returners.append(hungriest)
                attackers.remove(hungriest)

        for w in returners:
            environment.assign_group(w, "village")
        for w in attackers:
            environment.assign_group(w, "attack")

        if attackers:
            if self.first_attack_step is None:
                self.first_attack_step = step
            self.last_attack_step = step
```