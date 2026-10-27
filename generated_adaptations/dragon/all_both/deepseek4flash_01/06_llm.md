Looking at the failures, the root causes are:

1. **Starvation at step 6 (`initial_wheat=15`)**: The strategy spent wheat on spawning, leaving none for imminent meals. Spawning must reserve wheat for any villager who is about to need a meal.

2. **Dragon left unattacked 3+ steps in a row**: Warriors need a 3‑step round trip (move→eat→move) to feed, so a *single* attacker always creates a 3‑step hole. With synchronized warriors they all hit the "must rest" point together. The fix is to proactively rotate **one** warrior out to eat before others reach the danger threshold, which desynchronizes their meal cycles so at least one warrior is almost always attacking (allowing at most short, legal gaps).

3. **Late‑game gaps (steps 20–30)**: attrition of warriors. The strategy needs to keep spawning replacement warriors and avoid burning wheat needed for meals.

Key changes:
- Reserve wheat for imminent eaters before any spawn.
- Cave rotation returns only warriors at `steps_since_meal >= 4` (cannot attack), plus at most one *proactive* returner (hungriest with `>= 3`, or `>= 2` when many warriors are present) to stagger meal cycles.
- Eat villagers at `>= 5` (must) and warriors at `>= 2` (so they don't arrive in the Cave already needing to leave).
- Spawn plan interleaves warriors and farmers so both appear early, refreshable, using a reserve check.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.first_attack_step = None
        self.last_attack_step = None
        self.spawn_order = [
            "spawn warrior",
            "spawn farmer",
            "spawn warrior",
            "spawn farmer",
            "spawn warrior",
            "spawn warrior",
        ]
        self.spawn_index = 0

    # ------------------------------------------------------------------ #
    #  VILLAGE                                                            #
    # ------------------------------------------------------------------ #
    def assign_in_village(self, components, environment, group_ids, step: int):
        components = list(components)
        budget = int(environment.farm.wheat)
        eaten_ids = set()

        # 1) Villagers at the starvation boundary MUST eat now.
        for c in sorted(components, key=lambda x: x.steps_since_meal, reverse=True):
            if c.steps_since_meal >= 5 and budget > 0:
                environment.assign_group(c, "eat")
                eaten_ids.add(id(c))
                budget -= 1

        # 2) Warriors that came back (or got hungry) eat before going out,
        #    so they never arrive in the Cave already needing to leave.
        for c in sorted(components, key=lambda x: x.steps_since_meal, reverse=True):
            if id(c) in eaten_ids or c.role != "Warrior":
                continue
            if c.steps_since_meal >= 2 and budget > 0:
                environment.assign_group(c, "eat")
                eaten_ids.add(id(c))
                budget -= 1

        remaining = [c for c in components if id(c) not in eaten_ids]
        warriors = [c for c in remaining if c.role == "Warrior"]
        farmers = [c for c in remaining if c.role == "Farmer"]

        # 3) Fresh warriors go to the Cave. Hungry ones were already fed.
        for w in warriors:
            if w.steps_since_meal < 2:
                environment.assign_group(w, "cave")
            else:
                environment.assign_group(w, "farm")

        # 4) Reserve wheat for imminent meals so spawning never starves anyone.
        imminent = sum(
            1
            for c in components
            if c.steps_since_meal >= 4 and id(c) not in eaten_ids
        )
        reserve = imminent + 2

        # 5) Spawn plan (alternating warriors / farmers, warriors first).
        spawn_group = None
        spawners = []
        cands = sorted(farmers, key=lambda x: x.steps_since_meal)
        if len(cands) >= 2 and self.spawn_index < len(self.spawn_order):
            desired = self.spawn_order[self.spawn_index]
            cost = 12 if desired == "spawn warrior" else 10
            if budget - cost >= reserve:
                spawn_group = desired
                spawners = cands[:2]
                budget -= cost
                self.spawn_index += 1

        spawner_ids = {id(c) for c in spawners}
        for c in spawners:
            environment.assign_group(c, spawn_group)

        # 6) All other farmers stay and farm.
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

        can_attack = [w for w in warriors if w.steps_since_meal < 4]
        must_return = [w for w in warriors if w.steps_since_meal >= 4]

        # Proactive rotation: pull ONE warrior out to eat BEFORE everyone hits
        # the wall together. This staggers the meal cycles so the Dragon is
        # never left unattacked for more than a couple of steps.
        proactive = []
        if len(can_attack) >= 2:
            hungriest = max(can_attack, key=lambda w: w.steps_since_meal)
            if hungriest.steps_since_meal >= 3:
                proactive = [hungriest]
            elif hungriest.steps_since_meal >= 2 and len(can_attack) >= 3:
                proactive = [hungriest]

        returning = must_return + proactive
        returning_ids = {id(w) for w in returning}
        attackers = [w for w in warriors if id(w) not in returning_ids]

        # Safety net: never leave the Cave without an attacker if avoidable.
        if not attackers and can_attack:
            keep = min(can_attack, key=lambda w: w.steps_since_meal)
            if id(keep) in returning_ids:
                returning_ids.discard(id(keep))
                returning = [w for w in returning if id(w) != id(keep)]
            attackers = [keep]

        for w in returning:
            environment.assign_group(w, "village")
        for w in attackers:
            environment.assign_group(w, "attack")

        if attackers:
            if self.first_attack_step is None:
                self.first_attack_step = step
            self.last_attack_step = step
```