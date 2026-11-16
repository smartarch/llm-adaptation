## Diagnosis of the previous run

- **Wheat was wasted.** Wheat piled up to 150-170 while the bot spawned only about 3 warriors. The spawn cap and the one-warrior-at-a-time cycle left most of the economy unused.
- **The Dragon was left unattacked.** Warriors were sent out only when they were freshly fed, so the Cave often had 0-1 attackers. Whenever the Dragon went unattacked it regenerated 5 HP per step, and the net damage was close to zero (Game 1 ended with the Dragon at 78 HP).
- **Warriors cycled too slowly.** Warriors left the Cave too late or arrived too late, so attacking capacity dropped in the middle of the fight.

## Revised strategy: sustained warrior pressure

**Goal:** Keep as many warriors as possible attacking every step. Each attacking warrior deals 3 damage per step, and the Dragon regenerates only on steps with no attack.

**Village phase**

1. **Eat when hungry.** Villagers with `steps_since_meal >= 3` eat, as long as wheat is available. This keeps everyone far from the 6-step starvation limit.
2. **One early farmer.** Spawn one farmer as soon as 10 wheat and two free farmers are available. This meets the "at least one farmer" requirement and adds income.
3. **Warrior spawning every step possible.** Whenever at least 12 wheat is left and two free farmers exist, spawn one warrior. The cap is raised to 10, so the wheat is actually converted into damage. Farmers are the spawners, so the warriors stay in the Cave.
4. **Fed warriors go to the Cave.** Any warrior with `steps_since_meal <= 2` that was not used for spawning goes to the Cave while the Dragon is alive.
5. **Everyone else farms.**

**Cave phase**

- Warriors with `steps_since_meal >= 4` return to the Village to eat (recommended threshold). They have to return before starving.
- All other warriors attack every step, so the Dragon is never left unattacked while attackers remain.
- Farmers in the Cave return to the Village.

Each villager is assigned exactly once per phase, through a plan array.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Sustained warrior pressure:
      - Villagers that have not eaten for >= 3 steps eat in the Village.
      - One farmer is spawned early (requirement), then warriors are spawned
        whenever wheat allows (up to MAX_WARRIOR_SPAWNS), using two farmers as spawners.
      - Fed warriors go to the Cave; warriors in the Cave attack every step
        unless they have gone 4+ steps without eating, in which case they return to eat.
      - Farmers in the Cave are sent back to the Village.
    """

    MAX_WARRIOR_SPAWNS = 10
    MAX_FARMER_SPAWNS = 1
    EAT_THRESHOLD = 3          # Village: eat when steps_since_meal >= this
    CAVE_SAFE_THRESHOLD = 2    # Village: only send warriors to the Cave if steps_since_meal <= this
    CAVE_RETURN_THRESHOLD = 4  # Cave: go eat when steps_since_meal >= this

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.warriors_spawned = 0
        self.farmers_spawned = 0

    def assign_in_village(self, components, environment, group_ids, step: int):
        n = len(components)
        plan = [None] * n
        wheat = environment.farm.wheat
        dragon_alive = environment.dragon.hp > 0

        # 1) Eat first: villagers who are getting hungry.
        for i, c in enumerate(components):
            if c.steps_since_meal >= self.EAT_THRESHOLD and wheat >= 1:
                plan[i] = "eat"
                wheat -= 1

        def free(role=None):
            return [i for i, c in enumerate(components)
                    if plan[i] is None and (role is None or c.role == role)]

        # 2) One early farmer spawn (requirement, and adds wheat income).
        if self.farmers_spawned < self.MAX_FARMER_SPAWNS and wheat >= 10:
            spawners = free("Farmer")[:2]
            if len(spawners) == 2:
                for i in spawners:
                    plan[i] = "spawn farmer"
                wheat -= 10
                self.farmers_spawned += 1

        # 3) Warrior spawns whenever wheat allows (damage dealers).
        if self.warriors_spawned < self.MAX_WARRIOR_SPAWNS and wheat >= 12:
            spawners = free("Farmer")[:2]
            if len(spawners) < 2:
                spawners = free()[:2]
            if len(spawners) == 2:
                for i in spawners:
                    plan[i] = "spawn warrior"
                wheat -= 12
                self.warriors_spawned += 1

        # 4) Fed, unassigned warriors go to the Cave while the Dragon lives.
        for i, c in enumerate(components):
            if plan[i] is None and c.role == "Warrior":
                if dragon_alive and c.steps_since_meal <= self.CAVE_SAFE_THRESHOLD:
                    plan[i] = "cave"

        # 5) Everyone else farms.
        for i in range(n):
            if plan[i] is None:
                plan[i] = "farm"

        for c, g in zip(components, plan):
            environment.assign_group(c, g)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.role == "Farmer":
                group = "village"
            elif c.steps_since_meal >= self.CAVE_RETURN_THRESHOLD:
                group = "village"
            else:
                group = "attack"
            environment.assign_group(c, group)
```