New best (17.7) again from a larger farmer economy — the pattern is consistent: **more farmers = more spawn slots = more warriors per step = faster kill**. The farmer base is the true engine of the strategy.

Two refinements:
1. **Push the farmer target to 8 farmers.** At 8 farmers × 5 wheat = 40 wheat/step, we can fund ~3 warrior pairs per step while comfortably covering meal costs, sustaining a much larger simultaneous attacking force.
2. **Front-load a warrior or two in the first few steps** (before the big farmer ramp) to start chipping the dragon immediately and stop any regeneration — then greedily grow farmers, then mass warriors. This keeps early damage flowing while the economy scales.

Everything else (dynamic reserve, multi-pair spawning, fresh-warrior→Cave rule, attack unless starving ≥6, anti-regeneration guarantee) is retained.

```python
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.last_attack_step = -10
        self.early_warriors_spawned = 0

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        farmers = [c for c in components if c.role == 'Farmer']

        # Meals: mandatory at 5; warriors at >=3 cannot enter the Cave -> eat.
        to_eat = set()
        for c in components:
            if c.steps_since_meal >= 5:
                to_eat.add(c)
            elif c.role == 'Warrior' and c.steps_since_meal >= 3:
                to_eat.add(c)

        avail = [f for f in farmers if f not in to_eat]

        # Dynamic reserve: keep wheat only for imminent meals + small buffer.
        imminent = sum(1 for c in components if c.steps_since_meal >= 4)
        reserve = imminent + 2
        spend = max(0, wheat - reserve)
        spawn = {}

        # --- 0) Front-load a couple of early warriors to start attacking ---
        if (self.early_warriors_spawned < 2 and len(avail) >= 2
                and spend >= 12):
            spawn[avail[0]] = 'spawn warrior'
            spawn[avail[1]] = 'spawn warrior'
            avail = avail[2:]
            spend -= 12
            self.early_warriors_spawned += 1

        # --- 1) Grow the farmer economy to 8 (more wheat + spawn slots) ---
        TARGET_FARMERS = 8
        if len(farmers) < TARGET_FARMERS and len(avail) >= 2 and spend >= 10:
            max_pairs = min(
                len(avail) // 2,
                spend // 10,
                (TARGET_FARMERS - len(farmers) + 2) // 2,
            )
            for j in range(max_pairs):
                spawn[avail[2 * j]] = 'spawn farmer'
                spawn[avail[2 * j + 1]] = 'spawn farmer'
            avail = avail[2 * max_pairs:]
            spend -= 10 * max_pairs

        # --- 2) Spend everything left on warriors (multiple pairs/step) ---
        nw = min(len(avail) // 2, spend // 12)
        for j in range(nw):
            spawn[avail[2 * j]] = 'spawn warrior'
            spawn[avail[2 * j + 1]] = 'spawn warrior'

        # --- 3) Assign every component exactly once ----------------------
        for c in components:
            if c in to_eat:
                environment.assign_group(c, 'eat')
            elif c in spawn:
                environment.assign_group(c, spawn[c])
            elif c.role == 'Warrior' and c.steps_since_meal <= 2:
                environment.assign_group(c, 'cave')   # fed enough -> attack
            else:
                environment.assign_group(c, 'farm')   # farmers stay & farm

    def assign_in_cave(self, components, environment, group_ids, step: int):
        warriors = [c for c in components if c.role == 'Warrior']

        # Non-warriors shouldn't be here; starving warriors deal no damage.
        go_home = set(c for c in components if c.role != 'Warrior')
        for w in warriors:
            if w.steps_since_meal >= 6:
                go_home.add(w)

        attackers = [w for w in warriors if w not in go_home]

        # Guarantee the dragon is never left unattacked for > 2 steps.
        if not attackers and warriors and (step - self.last_attack_step) >= 3:
            keep = min(warriors, key=lambda x: x.steps_since_meal)
            go_home.discard(keep)
            attackers = [keep]

        attacked = False
        for c in components:
            if c in go_home:
                environment.assign_group(c, 'village')
            else:
                environment.assign_group(c, 'attack')
                attacked = True

        if attacked:
            self.last_attack_step = step
```