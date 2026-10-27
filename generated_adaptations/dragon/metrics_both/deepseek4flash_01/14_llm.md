New best (18.7) came from the 5-farmer economy. The remaining bottleneck is **warrior uptime and throughput**:

1. **Wasted warrior-turns**: warriors with `steps_since_meal == 3` in the village currently *farm* (useless) because the eat threshold was `>=4`. The rule says a warrior at `>=3` shouldn't go to the Cave and should eat first — so I lower the eat threshold to `>=3`, letting them reset one step sooner and attack again faster.
2. **More wheat → more warrior pairs per step**: I raise the farmer target from 5 to 6. At 30 wheat/step, we can sustain ~2 warrior pairs per step, keeping the Cave population (and damage output) high even as the dragon kills warriors. The extra mouths are easily covered by the increased farm yield.
3. Kept the proven pieces: dynamic reserve tied to imminent eaters, multi-pair spawning, fresh warriors (≤2 steps since meal) → Cave, attack unless starving (`≥6`), and the anti-regeneration guarantee.

```python
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.last_attack_step = -10

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

        # --- 1) Grow the farmer economy to 6 (more wheat + spawn slots) ---
        TARGET_FARMERS = 6
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