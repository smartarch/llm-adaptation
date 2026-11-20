## Analysis of the previous run

The win rate is 100% and the average is 22 steps, so the remaining gains are in speed. The logs show three limits:

- **The economy stops too early.** The farmer target of 6 was reached by step 8, and after that no new farmers were added. Income stayed around 25 to 35 wheat per step, and warrior production was limited by wheat rather than farmers.
- **Warrior output is slow at the start.** Warriors are the damage source (3 per attack against 1 for farmers), but they were only 1 to 2 for the first 10 steps in every game.
- **Dragon regeneration on idle steps.** Several steps had only 1 to 2 attackers, so the Dragon healed back 5 HP on those steps.

## Revised strategy

**Village phase**
1. **Meals stay mandatory.** Villagers with `steps_since_meal >= 2` eat first, and their wheat is deducted before any spawn decision. Starvation stays impossible.
2. **Longer economy phase.** Farmer spawns continue until 8 farmers exist or step 12 passes. Each farmer returns its 10-wheat cost in about two steps of farming, so growing the farm early pays off more than early warriors.
3. **Warriors take all remaining wheat.** Once the economy phase ends, every pair of free farmers spawns a warrior whenever wheat is at least 12. Spawning is uncapped per step.
4. **Rotation.** Warriors that are not eating or spawning go to the cave. Farmers farm.

**Cave phase**
- Farmers return to the village.
- Warriors attack while `steps_since_meal < 4`. At 4 they return to eat, which keeps the 6-step starvation limit out of reach.
- Once the Dragon is dead, the remaining villagers wait in the cave.

Changes from the previous version: the farmer target rises from 6 to 8, the economy window extends from step 8 to step 12, and the rest of the logic is unchanged so the verified safety properties still hold. The expected effect is a larger farm earlier, which should allow more warriors to attack in the middle of the fight.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Village:
      1. Mandatory meals: villagers with steps_since_meal >= 2 eat (paid first).
      2. Economy: while total farmers < FARMER_TARGET and step <= ECONOMY_STEPS,
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
    ECONOMY_STEPS = 12
    FARMER_TARGET = 8
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

        # 2) Economy: grow the farmer population while it pays back quickly.
        if step <= self.ECONOMY_STEPS:
            while (len(free_farmers) >= 2
                   and total_farmers < self.FARMER_TARGET
                   and wheat >= self.FARMER_COST):
                a, b = free_farmers.pop(), free_farmers.pop()
                assigned[id(a)] = "spawn farmer"
                assigned[id(b)] = "spawn farmer"
                wheat -= self.FARMER_COST
                total_farmers += 1

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