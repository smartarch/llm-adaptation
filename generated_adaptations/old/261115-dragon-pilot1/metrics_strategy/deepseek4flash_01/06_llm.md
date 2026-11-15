**Root-cause rethink:** My earlier versions fumbled two mechanics:
- A villager in the **"cave" group does NOT trigger Dragon retaliation** — the Dragon only reacts when *attacked*. Also, **before the first attack the Dragon never regenerates.** So the optimal opening is to *stockpile* warriors (farming for wheat meanwhile) and then "alpha-strike," rather than trickling into the Cave and feeding the Dragon free kills/regen.
- Spawners are **not consumed** — 2 villagers in a spawn group produce 1 new villager per step while wheat is paid. So I must reserve 2 "breeder" farmers and keep enough *other* farmers (≥3) to fund them, while never letting the wheat buffer hit 0 (eating competes for wheat).

**Strategy:**
1. **Eat** any villager at `steps_since_meal >= 5`; feed warriors at `>= 4` so a warrior never enters combat starving (starving → 0 damage).
2. **Warrior-stockpiling phase (until `>= ~8` warriors spawned or step 12):** warriors *farm* in the Village (2 wheat each) instead of attacking — building the army and economy without waking the Dragon. They're kept fed here where food is free of travel.
3. **War phase:** all Village warriors go to the Cave; Cave warriors **attack** while fed and only return to the Village to eat (`>= 4`), then immediately rejoin.
4. **Economy:** keep up to 2 "spawn warrior" breeders once there are ≥5 farmers (so ≥3 farmers still fund the 12-wheat cost + eating). Early on, spawn farmers to grow a small population. Everything else farms. Spawning only happens when a wheat buffer (≥14) exists so nobody starves.
5. Forced trigger at step ~12 guarantees the first attack well inside 15 steps.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.spawned_warriors = 0
        self.spawned_farmers = 0
        self.war_started = False
        self.target_warriors = 8
        self.wheat_buffer = 14

    # ---------------- Village ----------------
    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        assigned = set()

        def A(c, g):
            environment.assign_group(c, g)
            assigned.add(id(c))

        # 1. Urgent meals (never let anyone reach the 6-step starvation mark).
        for c in sorted(components, key=lambda x: -x.steps_since_meal):
            if id(c) in assigned:
                continue
            if c.steps_since_meal >= 5 and wheat > 0:
                A(c, 'eat')
                wheat -= 1

        # Decide whether the war has begun (army big enough OR deadline near).
        if not self.war_started:
            if self.spawned_warriors >= self.target_warriors or step >= 12:
                self.war_started = True

        # 2. Warriors in the Village.
        for c in components:
            if id(c) in assigned or c.role != 'Warrior':
                continue
            if c.steps_since_meal >= 4 and wheat > 0:
                A(c, 'eat')
                wheat -= 1
            elif self.war_started:
                A(c, 'cave')      # head to the battlefield
            else:
                A(c, 'farm')      # help the economy while the army builds

        # 3. Farmers.
        farmers = [c for c in components
                   if id(c) not in assigned and c.role == 'Farmer']

        # Early: grow a tiny population so the economy can bootstrap.
        if len(components) < 5 and len(farmers) >= 2 and wheat >= 12 and step <= 8:
            A(farmers[0], 'spawn farmer')
            A(farmers[1], 'spawn farmer')
            self.spawned_farmers += 1
            farmers = farmers[2:]

        # Build the warrior army: keep 2 breeders while >= 5 farmers remain
        # (so at least 3 farmers still fund the 12-wheat cost plus meals).
        if len(farmers) >= 5 and wheat >= self.wheat_buffer and 'spawn warrior' in group_ids:
            A(farmers[0], 'spawn warrior')
            A(farmers[1], 'spawn warrior')
            self.spawned_warriors += 1
            farmers = farmers[2:]

        # Everyone else farms.
        for f in farmers:
            A(f, 'farm')

    # ---------------- Cave -------------------
    def assign_in_cave(self, components, environment, group_ids, step: int):
        assigned = set()

        def A(c, g):
            environment.assign_group(c, g)
            assigned.add(id(c))

        # Non-warriors have no business in the Cave.
        for c in components:
            if c.role != 'Warrior':
                A(c, 'village')

        # Warriors: attack while fed, otherwise go home to eat.
        for c in components:
            if id(c) in assigned:
                continue
            if c.steps_since_meal >= 4:
                A(c, 'village')   # return to eat, come back fed
            else:
                A(c, 'attack')
```