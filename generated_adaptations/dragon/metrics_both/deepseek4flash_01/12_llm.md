Looking at the trajectory (23.0 → 19.3 → 19.0 → 22.3), the key lessons are:
- Multi-pair warrior spawning and a dynamic wheat reserve were the big wins (23→19).
- Rushing warriors at the expense of farmers (22.3) was a regression — so **more farmer economy**, not less, is the correct direction.
- 19.0's structure is the best baseline.

The remaining bottleneck is **warrior throughput**: we're limited by how many farmers are available to spawn warriors each turn. Building to 5 farmers (instead of 4) gives more wheat/turn and more spawn slots, enabling more warrior pairs per step — while still leaving 2 required farmers satisfied. I keep everything else from the proven 19.0 structure (dynamic reserve, multi-pair warrior spawning, warriors ≤2 steps since meal → Cave, attack unless starving ≥6).

```python
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.last_attack_step = -10

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        farmers = [c for c in components if c.role == 'Farmer']

        # Meals: mandatory at 5; warriors >=4 cannot enter the Cave anyway.
        to_eat = set()
        for c in components:
            if c.steps_since_meal >= 5:
                to_eat.add(c)
            elif c.role == 'Warrior' and c.steps_since_meal >= 4:
                to_eat.add(c)

        avail = [f for f in farmers if f not in to_eat]

        # Dynamic reserve: keep wheat only for imminent meals + small buffer.
        imminent = sum(1 for c in components if c.steps_since_meal >= 4)
        reserve = imminent + 2
        spend = max(0, wheat - reserve)
        spawn = {}

        # --- 1) Grow the farmer economy to 5 (more wheat + spawn slots) ---
        TARGET_FARMERS = 5
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