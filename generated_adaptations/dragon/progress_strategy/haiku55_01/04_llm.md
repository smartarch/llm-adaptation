## Analysis of the previous runs

- **Wheat was the bottleneck.** Farmers were repeatedly pulled off the farm to spawn or eat, so wheat income collapsed to a few units per step. In Game 1, wheat sat between 1 and 28 for most of the game, which delayed warrior spawns.
- **Warriors were idle in transit.** Warriors often went back and forth to eat with no attacks in between. In Game 3, the attack count was 0 on several steps.
- **Dragon regeneration erased progress.** Whenever the attack rate dropped, the Dragon healed 5 HP per step (Game 1 went from 88 to 93 and 94 to 99 when attacks paused).
- **Spawning was too slow.** The old code limited spawns to one farmer pair per step and kept a large wheat reserve, so the warrior army grew too slowly.

## Revised strategy

**Village phase**
1. **Mandatory meals first.** Any villager with `steps_since_meal >= 2` eats (the old code allowed this but also let budget checks skip eating). Meals are paid before anything else, so no one starves.
2. **Economy first, then army.** During the first 5 steps, pairs of free farmers spawn farmers (10 wheat) while wheat allows. This grows the farm income early, since each new farmer makes about 5 wheat per step.
3. **Warrior production.** After that, free farmers in pairs spawn warriors (12 wheat) as often as wheat allows, with no fixed cap per step. Warriors are the damage dealers, so the army is built as fast as the farm can fund it.
4. **Rotation.** Warriors that are in the village and not eating go to the cave. Everyone else farms.

**Cave phase**
- Farmers return to the village.
- Warriors attack while `steps_since_meal < 4`. At 4 they return to eat, arriving with `steps_since_meal` of about 5, which stays below the 6-step starvation limit. This keeps the warrior pool attacking most of the time while avoiding starvation.
- Once the Dragon is dead, the remaining villagers stay in the cave.

The main changes from the previous version are: meals are paid before spawns so starvation is avoided, the wheat budget is computed correctly, spawns are no longer capped at one pair per step, and the cave return threshold is longer, which means more attack steps per warrior.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Village:
      1. Mandatory meals: villagers with steps_since_meal >= 2 eat.
      2. Early economy (steps <= 5): free farmers in pairs spawn farmers (10 wheat).
      3. Army: free farmers in pairs spawn warriors (12 wheat) with the remaining wheat.
      4. Warriors not eating/spawning go to the cave; everyone else farms.
    Cave:
      - Farmers return to the village.
      - Warriors attack while steps_since_meal < 4; otherwise they return to eat.
      - Once the Dragon is dead, everyone waits in the cave.
    """

    EAT_THRESHOLD = 2
    CAVE_ATTACK_LIMIT = 4
    ECONOMY_STEPS = 5
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

        # Free farmers that are not eating are candidates for spawning.
        free_farmers = [c for c in components
                        if c.role == "Farmer" and id(c) not in assigned]

        # 2) Economy spawns early on.
        if step <= self.ECONOMY_STEPS:
            while len(free_farmers) >= 2 and wheat >= self.FARMER_COST:
                a, b = free_farmers.pop(), free_farmers.pop()
                assigned[id(a)] = "spawn farmer"
                assigned[id(b)] = "spawn farmer"
                wheat -= self.FARMER_COST

        # 3) Warrior spawns with remaining wheat.
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