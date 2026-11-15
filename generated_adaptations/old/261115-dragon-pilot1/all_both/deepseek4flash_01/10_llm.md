Looking at the remaining failures, two distinct problems remain:

1. **"Dragon not killed"** (seed=3, seed=1+wheat) – total damage throughput is too low. The spawn pipeline isn't producing warriors fast enough and too much wheat is being hoarded for spawns.
2. **"Unattacked >2 steps"** at step 27 – a late‑game coverage hole where warriors' meal cycles drift into sync.

The key insight I was missing is that warrior meal times **are the phase clock**. All warriors reset `steps_since_meal` to 0 when they eat, so keeping them "in phase" causes the 3‑step round trip (travel → eat → travel) to happen simultaneously for everyone. To break this without delaying hungry warriors (which would break the "don't send `ssm>=3` to cave" rule), the meals themselves must be staggered: feed **one non‑urgent warrior per step** (hungriest first), while the mandatory `ssm>=5` meals always go through. That desynchronizes their return trips over time. Combined with a proactive stagger in the Cave (pull the hungriest attacker out only when there are 3+ attackers, so 2+ keep firing) this spreads the gaps.

To fix damage throughput, the spawn order now guarantees **one warrior first** (early attack), then **two farmers**, then **another warrior**, then continues spawning warriors as long as a meal reserve is kept. This keeps the warrior count high enough for continuous rotation.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.spawned_warriors = 0
        self.spawned_farmers = 0

    # ------------------------------------------------------------------ #
    #  VILLAGE                                                            #
    # ------------------------------------------------------------------ #
    def assign_in_village(self, components, environment, group_ids, step: int):
        comps = list(components)
        budget = int(environment.farm.wheat)
        eaten = set()

        # 1) Mandatory starvation protection (all roles).
        for c in sorted(comps, key=lambda x: x.steps_since_meal, reverse=True):
            if c.steps_since_meal >= 5 and budget > 0:
                environment.assign_group(c, "eat")
                eaten.add(id(c))
                budget -= 1

        # 2) Farmers proactively eat slightly early.
        for c in comps:
            if id(c) in eaten or c.role == "Warrior":
                continue
            if c.steps_since_meal >= 4 and budget >= 3:
                environment.assign_group(c, "eat")
                eaten.add(id(c))
                budget -= 1

        # 3) Warriors: feed ONLY the hungriest one per step. This is what
        #    desynchronizes their meal cycles (= their Cave round trips),
        #    which is what keeps the Dragon under continuous fire.
        need = sorted(
            [
                c
                for c in comps
                if c.role == "Warrior"
                and id(c) not in eaten
                and c.steps_since_meal >= 2
            ],
            key=lambda x: x.steps_since_meal,
            reverse=True,
        )
        if need and budget > 0:
            w = need[0]
            environment.assign_group(w, "eat")
            eaten.add(id(w))
            budget -= 1

        remaining = [c for c in comps if id(c) not in eaten]
        warriors = [c for c in remaining if c.role == "Warrior"]
        farmers = [c for c in remaining if c.role == "Farmer"]

        # 4) Fresh warriors travel to the Cave.
        for w in warriors:
            if w.steps_since_meal <= 1:
                environment.assign_group(w, "cave")
            else:
                environment.assign_group(w, "farm")

        # 5) Spawn plan. Keep a small meal reserve so feeding never fails.
        imminent = sum(
            1 for c in comps if c.steps_since_meal >= 4 and id(c) not in eaten
        )
        reserve = imminent + 1

        spawn_group = None
        spawners = []
        cands = sorted(farmers, key=lambda x: x.steps_since_meal)

        if len(cands) >= 2:
            want = None
            if self.spawned_warriors < 1 and budget - 12 >= reserve:
                want = ("spawn warrior", 12)      # early attack
            elif self.spawned_farmers < 2 and budget - 10 >= reserve:
                want = ("spawn farmer", 10)       # economy
            elif budget - 12 >= reserve:
                want = ("spawn warrior", 12)      # sustain DPS
            elif self.spawned_farmers < 2 and budget - 10 >= reserve:
                want = ("spawn farmer", 10)

            if want:
                spawn_group, cost = want
                spawners = cands[:2]
                budget -= cost
                if spawn_group == "spawn warrior":
                    self.spawned_warriors += 1
                else:
                    self.spawned_farmers += 1

        spawner_ids = {id(c) for c in spawners}
        for c in spawners:
            environment.assign_group(c, spawn_group)

        # 6) All remaining farmers farm.
        for c in farmers:
            if id(c) not in spawner_ids:
                environment.assign_group(c, "farm")

    # ------------------------------------------------------------------ #
    #  CAVE                                                               #
    # ------------------------------------------------------------------ #
    def assign_in_cave(self, components, environment, group_ids, step: int):
        comps = list(components)
        warriors = [c for c in comps if c.role == "Warrior"]

        for c in comps:
            if c.role != "Warrior":
                environment.assign_group(c, "village")

        if not warriors:
            return

        # Attackers stay until they MUST leave (ssm would reach 5).
        capable = [w for w in warriors if w.steps_since_meal <= 3]
        forced = [w for w in warriors if w.steps_since_meal >= 4]

        # Proactive stagger: only when there is real redundancy, pull the
        # hungriest attacker out so 2+ warriors keep firing. This spreads
        # the meal trips of a group instead of letting them bunch up.
        if len(capable) >= 3:
            h = max(capable, key=lambda w: w.steps_since_meal)
            if h.steps_since_meal >= 3:
                capable.remove(h)
                forced.append(h)

        for w in forced:
            environment.assign_group(w, "village")
        for w in capable:
            environment.assign_group(w, "attack")
```