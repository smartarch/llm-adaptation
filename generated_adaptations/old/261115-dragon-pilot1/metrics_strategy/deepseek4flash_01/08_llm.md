**What was going wrong.** I was either sending warriors too early (1–2 weak warriors whose meal trips created gaps → the Dragon regenerated +5 in every gap step, undoing damage), or letting the economy collapse. Two mechanics I'm now exploiting explicitly:

1. **The Dragon does not regenerate before the first attack.** So it is *free* to stockpile warriors first, then hit it with a continuous attack once we can keep at least one warrior attacking nearly every step.
2. **Farmers in the Village are never eaten** (the Dragon only harms villagers in the Cave) and produce 5 wheat each — so the safe, self-sustaining economy is a farmer base plus a "spawn warrior" breeding pair, funneling warriors into the Cave.

**New strategy — "stockpile, then sustain":**
- **Eat first:** Villagers at `steps_since_meal ≥ 5` eat; Cave-returning warriors eat at `≥ 4` so nobody ever hits the starvation step (starving warriors deal 0 damage).
- **Build phase (until step ≥ 7 with ≥ 3 warriors, or forced by step 11):** grow to ~5 farmers, then spawn warriors with 2 farmer "breeders" while keeping the rest farming. **Warriors wait in the Village** (farming for extra wheat) — the Dragon stays at 100 with no regen, so nothing is lost by waiting.
- **War phase:** all Village warriors go to the Cave; Cave warriors **attack** and only return to the Village to eat (`≥ 4`), then immediately rejoin. Warriors spawned at different steps have **staggered meal timers**, so some are always attacking — keeping regeneration near zero.
- **Sustain:** during the war, keep spawning replacement warriors (they get eaten ~20% of attack steps) so the army never collapses; farmers are protected and keep the wheat flowing.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.release = False          # has the alpha-strike begun?
        self.spawned_warriors = 0
        self.spawned_farmers = 0

    # ------------------------- Village -------------------------
    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        assigned = set()

        def A(c, g):
            environment.assign_group(c, g)
            assigned.add(id(c))

        # Decide whether to launch the assault.
        warriors_here = sum(
            1 for c in components
            if c.role == 'Warrior' and id(c) not in assigned
        )
        if (step >= 7 and warriors_here >= 3) or step >= 11:
            self.release = True

        # 1) Eat urgent villagers so nobody reaches the starvation step.
        for c in sorted(components, key=lambda x: -x.steps_since_meal):
            if id(c) in assigned:
                continue
            if c.steps_since_meal >= 5 and wheat > 0:
                A(c, 'eat')
                wheat -= 1

        # 2) Warriors.
        for c in components:
            if id(c) in assigned or c.role != 'Warrior':
                continue
            if c.steps_since_meal >= 4 and wheat > 0:
                A(c, 'eat')          # must be fed to matter in the Cave
                wheat -= 1
            elif self.release:
                A(c, 'cave')         # head to the battlefield
            else:
                A(c, 'farm')         # hold & help economy; Dragon not woken

        # 3) Farmers: bootstrap economy, then breed warriors.
        farmers = [c for c in components
                   if id(c) not in assigned and c.role == 'Farmer']
        n = len(farmers)
        total_farmers = n + self.spawned_farmers

        if not self.release:
            if total_farmers < 5 and n >= 2 and wheat >= 12:
                A(farmers[0], 'spawn farmer')
                A(farmers[1], 'spawn farmer')
                self.spawned_farmers += 1
                farmers = farmers[2:]; n -= 2; wheat -= 10
            elif n >= 3 and wheat >= 14:
                A(farmers[0], 'spawn warrior')
                A(farmers[1], 'spawn warrior')
                self.spawned_warriors += 1
                farmers = farmers[2:]; n -= 2; wheat -= 12
            elif n >= 2 and wheat >= 12:
                A(farmers[0], 'spawn farmer')
                A(farmers[1], 'spawn farmer')
                self.spawned_farmers += 1
                farmers = farmers[2:]; n -= 2; wheat -= 10
        else:
            # War phase: keep replacement warriors coming.
            if n >= 4 and wheat >= 14:
                A(farmers[0], 'spawn warrior')
                A(farmers[1], 'spawn warrior')
                self.spawned_warriors += 1
                farmers = farmers[2:]; n -= 2; wheat -= 12
            if n >= 7 and wheat >= 26:
                A(farmers[0], 'spawn warrior')
                A(farmers[1], 'spawn warrior')
                self.spawned_warriors += 1
                farmers = farmers[2:]; n -= 2; wheat -= 12

        # 4) Everyone remaining farms.
        for f in farmers:
            A(f, 'farm')

    # --------------------------- Cave --------------------------
    def assign_in_cave(self, components, environment, group_ids, step: int):
        assigned = set()

        def A(c, g):
            environment.assign_group(c, g)
            assigned.add(id(c))

        # Non-warriors never fight; send them home.
        for c in components:
            if c.role != 'Warrior':
                A(c, 'village')

        # Warriors: attack while fed; return home to eat well before starving.
        for c in components:
            if id(c) in assigned:
                continue
            if c.steps_since_meal >= 4:
                A(c, 'village')     # go eat, then come straight back
            else:
                A(c, 'attack')
```