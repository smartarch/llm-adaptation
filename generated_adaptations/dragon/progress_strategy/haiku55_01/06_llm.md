## Analysis of the previous run

The 100% win rate is good, but the games still took 19 to 25 steps. Three things limited the speed:

- **Early economy was too small.** Only one farmer pair was spawned early on, so the farm produced about 15 wheat per step for too long. A farmer costs 10 wheat and returns 5 wheat per step, so it pays for itself in two steps. Growing the farmer count quickly early on pays off.
- **Warrior production started late.** Warrior spawns only began once the farmer economy was up. Warriors deal 3 damage per attack compared with 1 for farmers, so they are the main damage source.
- **Damage was intermittent.** In Game 3, only 1 to 4 warriors attacked each step, and the Dragon regenerated 5 HP on steps with no attacks.

## Revised strategy

**Village phase**
1. **Meals stay mandatory.** Any villager with `steps_since_meal >= 2` eats first, so starvation remains impossible.
2. **Farmer economy up to a target.** While the farm has fewer than 6 farmers and the step is at most 8, free farmers are paired into `spawn farmer` whenever wheat allows. The early spawns compound.
3. **Warriors with all remaining wheat.** After the economy target is met, every pair of free farmers goes to `spawn warrior` whenever at least 12 wheat is available, with no cap per step.
4. **Rotation.** Warriors that are not eating or spawning go to the cave. Farmers farm.

**Cave phase**
- Farmers return to the village.
- Warriors attack while `steps_since_meal < 4`. At 4 they return to eat, so they never reach the 6-step starvation limit.
- Once the Dragon is dead, everyone waits in the cave.

The main changes are a larger early farmer economy and an uncapped warrior production rate. Together these should raise the number of attacking warriors sooner, which shortens the fight.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Village:
      1. Mandatory meals: villagers with steps_since_meal >= 2 eat.
      2. Economy: while farmers < FARMER_TARGET and step <= ECONOMY_STEPS,
         pairs of free farmers spawn farmers (10 wheat).
      3. Army: pairs of free farmers spawn warriors (12 wheat), uncapped.
      4. Warriors not eating/spawning go to the cave; everyone else farms.
    Cave:
      - Farmers return to the village.
      - Warriors attack while steps_since_meal < CAVE_ATTACK_LIMIT; otherwise return to eat.
      - Once the Dragon is dead, everyone waits in the cave.
    """

    EAT_THRESHOLD = 2
    CAVE_ATTACK_LIMIT = 4
    ECONOMY_STEPS = 8
    FARMER_TARGET = 6
    FARMER_COST = 10
    WARRIOR_COST = 12

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        assigned = {}

        # 1) Mandatory meals (paid first so nobody starves).
        eaters = [c for c in components if c.steps_since_meal >= self.EAT_THRESHOLD]
        for c in eaters:
            assigned[id(c)] = "eat"
        wheat -= len(eaters)

        # Free farmers not eating are candidates for spawning.
        free_farmers = [c for c in components
                        if c.role == "Farmer" and id(c) not in assigned]
        # Farmers never leave the village, so this is the total farmer count.
        total_farmers = sum(1 for c in components if c.role == "Farmer")

        # 2) Early economy: grow the farmer population while it pays back quickly.
        if step <= self.ECONOMY_STEPS:
            while (len(free_farmers) >= 2
                   and total_farmers < self.FARMER_TARGET
                   and wheat >= self.FARMER_COST):
                a, b = free_farmers.pop(), free_farmers.pop()
                assigned[id(a)] = "spawn farmer"
                assigned[id(b)] = "spawn farmer"
                wheat -= self.FARMER_COST
                total_farmers += 1  # spawned farmer counted toward the target

        # 3) Army: warriors with all remaining wheat.
        while len(free_farmers) >= 2 and wheat >= self.WARRIOR_COST:
            a, b = free_farmers.pop(), free_farmers.pop()
            assigned[id(a)] = "spawn warrior"
            assigned[id(b)] = "spawn warrior"
            wheat -= self.WARRIOR_COST

        # 4) Remaining villagers: warriors go to the cave, farmers farm.
        for c in components:
            if id(c) in assigned:
                continue
            if c.role == "Warrior":
                assigned[id(c)] = "cave"
            else:
                assigned[id(c)] = "farm"

        for c in components:
            environment.assign_group(c, assigned[id(c)])

    def assign_in_cave(self, components, environment, group_ids, step: int):
        dragon_alive = environment.dragon.hp > 0
        for c in components:
            if c.role == "Farmer":
                environment.assign_group(c, "village")
            elif c.steps_since_meal >= self.CAVE_ATTACK_LIMIT:
                environment.assign_group(c, "village")
            elif dragon_alive:
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "cave")
```