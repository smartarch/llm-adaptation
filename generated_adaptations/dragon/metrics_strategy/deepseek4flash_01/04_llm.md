**Diagnosis:** The previous code spawned too few warriors (only 2) and staggered them, so the Dragon kept regenerating and there was never enough damage output within 30 steps. Additionally, warriors weren't being replaced, and the early game economy wasn't focused.

**New strategy — "alpha strike swarm":**
1. **Build phase (steps 0–9):** Keep warriors at home *farming* (they contribute 2 wheat each) instead of trickling into the Cave one at a time. This avoids weak, isolated attacks that trigger Dragon retaliation and regen for almost no damage. Meanwhile, farmers spawn warriors every step while wheat allows (leaving farmers to keep producing).
2. **Release:** Once ~7 warriors exist (or step ≥ 9, guaranteeing an attack well within 15 steps), send all warriors into the Cave **simultaneously** to attack in parallel. This maximizes damage per step and minimizes the number of Dragon retaliation events.
3. **Meals:** Mandatory eat at `steps_since_meal >= 5`; warriors also eat before reaching that threshold when possible. Held/fresh warriors with `steps_since_meal < 4` go straight to the Cave.
4. **Cave logic:** Farmers return to the Village; warriors attack until `steps_since_meal == 4`, then return home to eat and immediately come back.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.spawned_warriors = 0
        self.spawned_farmers = 0
        self.target_warriors = 8
        self.target_farmers = 4
        self.release_step = 9          # ensure first attack well within 15
        self.release_threshold = 7     # or release once this army size reached

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        assigned = set()

        def assign(c, g):
            environment.assign_group(c, g)
            assigned.add(id(c))

        comps = sorted(components, key=lambda c: -c.steps_since_meal)

        # 1. Mandatory meals: anyone at 5+ steps without food must eat now.
        for c in comps:
            if id(c) in assigned:
                continue
            if c.steps_since_meal >= 5 and wheat > 0:
                assign(c, 'eat')
                wheat -= 1

        # 2. Warriors: eat when stale, otherwise hold at home (build phase)
        #    or go to the Cave once the army is ready.
        army_ready = (
            self.spawned_warriors >= self.release_threshold
            or step >= self.release_step
        )
        for c in comps:
            if id(c) in assigned:
                continue
            if c.role == 'Warrior':
                if c.steps_since_meal >= 4 and wheat > 0:
                    assign(c, 'eat')
                    wheat -= 1
                elif not army_ready:
                    # Hold at home and contribute wheat until the strike.
                    assign(c, 'farm')
                else:
                    assign(c, 'cave')

        # 3. Farmers: spawn warriors aggressively, keep a farming base.
        farmers = [
            c for c in comps
            if id(c) not in assigned and c.role == 'Farmer'
        ]

        # Spawn warriors to build the alpha-strike army.
        while (
            self.spawned_warriors < self.target_warriors
            and wheat >= 12
            and len(farmers) >= 3
            and step <= 24
        ):
            a = farmers.pop(0)
            b = farmers.pop(0)
            assign(a, 'spawn warrior')
            assign(b, 'spawn warrior')
            wheat -= 12
            self.spawned_warriors += 1

        # Spawn a few extra farmers to sustain the economy / replace losses.
        while (
            self.spawned_farmers < self.target_farmers
            and wheat >= 10
            and len(farmers) >= 3
        ):
            a = farmers.pop(0)
            b = farmers.pop(0)
            assign(a, 'spawn farmer')
            assign(b, 'spawn farmer')
            wheat -= 10
            self.spawned_farmers += 1

        # Remaining farmers work the farm.
        for c in farmers:
            assign(c, 'farm')

    def assign_in_cave(self, components, environment, group_ids, step: int):
        assigned = set()

        def assign(c, g):
            environment.assign_group(c, g)
            assigned.add(id(c))

        # Non-warriors do not belong in the Cave.
        for c in components:
            if c.role != 'Warrior':
                assign(c, 'village')

        # Warriors attack in parallel; retreat only to eat.
        for c in components:
            if id(c) in assigned:
                continue
            if c.steps_since_meal >= 4:
                assign(c, 'village')
            else:
                assign(c, 'attack')
```