Looking at the 19-turn plateau, the dominant inefficiency is **dragon regeneration during attack gaps**. With only 1–2 warriors early, each warrior's return-trip (travel home + eat + travel back = ~3 steps) leaves the dragon unattacked → +5 HP per gap. The fix isn't micro-tuning meals — it's **getting to ≥3–4 warriors in the Cave as fast as possible**, because once warriors outnumber their eating trips, attacks become continuous.

Previous code also **built farmers first**, delaying the warrior pipeline. Since the requirement is only that "a few" farmers be spawned *over the game* (not immediately), I now **rush warriors first** to stop regeneration gaps early, then spawn the 2 required farmers once a warrior core exists, and grow the farmer base only when wheat is genuinely surplus (to enable multi-pair warrior bursts later).

Other refinements:
- Wheat reserve is now tied to **actual imminent eaters** (`len(to_eat)+1`) instead of a conservative population count, freeing wheat for earlier warrior spawns.
- Multi-pair warrior spawning from all available farmers each step (burst economy).
- Required 2 farmers have a hard deadline (`step >= 13`) so the functional requirement is always satisfied even under wheat pressure.
- Cave logic unchanged in spirit: attack all non-starving warriors (`steps_since_meal < 6`); starved ones (≥6) return to eat. No risky "keep a starving warrior" hack, since that can starve a warrior to death.

```python
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.last_attack_step = -10
        self.spawned_farmers = 0
        self.spawned_warriors = 0

    def _spawn_pairs(self, free, group, cost, max_pairs, spend, spawn):
        """Assign up to max_pairs disjoint pairs of `free` villagers to spawn."""
        n, i = 0, 0
        while n < max_pairs and i + 1 < len(free) and spend >= cost:
            spawn[free[i]] = group
            spawn[free[i + 1]] = group
            i += 2
            n += 1
            spend -= cost
        return free[i:], n, spend

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        farmers = [c for c in components if c.role == 'Farmer']

        # --- meals: mandatory at 5; warriors at >=3 must eat (rule) ---
        to_eat = set()
        for c in components:
            if c.steps_since_meal >= 5:
                to_eat.add(c)
            elif c.role == 'Warrior' and c.steps_since_meal >= 3:
                to_eat.add(c)

        free_farmers = [f for f in farmers if f not in to_eat]

        # Keep only what is needed for this turn's meals plus a small buffer.
        reserve = len(to_eat) + 1
        spend = max(0, wheat - reserve)
        spawn = {}

        # --- decide whether to spawn farmers this turn ---
        owe_farmers = self.spawned_farmers < 2
        do_farmers, fcap = False, 0
        if owe_farmers and (self.spawned_warriors >= 3 or step >= 13):
            # Warror core exists or deadline reached -> fulfil farmer requirement
            do_farmers = True
            fcap = 2 - self.spawned_farmers
        if (not owe_farmers) and len(farmers) < 4 \
                and self.spawned_warriors >= 3 and wheat >= 34:
            # Surplus wheat -> grow farmer base a little for burst spawning
            do_farmers = True
            fcap = max(fcap, (4 - len(farmers) + 1) // 2)

        if do_farmers and fcap > 0:
            free_farmers, nf, spend = self._spawn_pairs(
                free_farmers, 'spawn farmer', 10, fcap, spend, spawn)
            self.spawned_farmers += nf

        # --- spend the rest on warriors (multiple pairs per step!) ---
        free_farmers, nw, spend = self._spawn_pairs(
            free_farmers, 'spawn warrior', 12, 999, spend, spawn)
        self.spawned_warriors += nw

        # --- assign every component exactly once ---
        for c in components:
            if c in to_eat:
                environment.assign_group(c, 'eat')
            elif c in spawn:
                environment.assign_group(c, spawn[c])
            elif c.role == 'Warrior' and c.steps_since_meal <= 2:
                environment.assign_group(c, 'cave')   # fresh -> go attack
            else:
                environment.assign_group(c, 'farm')

    def assign_in_cave(self, components, environment, group_ids, step: int):
        warriors = [c for c in components if c.role == 'Warrior']

        # Non-warriors shouldn't be here; send them home.
        go_home = set(c for c in components if c.role != 'Warrior')

        # Starving warriors (6+ steps) deal no damage -> return to eat.
        for w in warriors:
            if w.steps_since_meal >= 6:
                go_home.add(w)

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