## Adaptation strategy

The strategy has two phases, one per decision function.

**Village phase (`assign_in_village`)**
1. **Feeding first.** Any villager with `steps_since_meal >= 2` goes to `eat`. Eating is limited by the wheat budget, so the strategy never plans more meals than the farm can cover. Starvation is the main threat, since a starving warrior deals no damage.
2. **Warrior spawning.** Warriors are the damage dealers, so when the remaining wheat allows it, two farmers are put in `spawn warrior` (12 wheat). The strategy keeps a meal reserve of one wheat per villager so the population can keep eating.
3. **Farmer spawning.** With wheat left over after the warrior spawns and reserve, pairs of farmers are put in `spawn farmer` (10 wheat). This grows the wheat economy.
4. **Warriors ready for combat.** Warriors that just ate (`steps_since_meal <= 1`) go to `cave`. Warriors that have not eaten yet wait for their turn at the trough.
5. **Everyone else farms.** Farmers that are not eating or spawning stay on `farm`.

**Cave phase (`assign_in_cave`)**
- Farmers are sent back to the Village, because they are not meant to fight.
- Warriors with `steps_since_meal < 3` attack the Dragon. A warrior that reaches 3 steps without a meal returns to the Village to eat, which keeps it well short of the 6-step starvation limit. The return trip costs one step, so the 3-step threshold leaves margin.
- If the Dragon is already dead, the remaining villagers stay in the cave.

The Dragon regenerates only on steps when nobody attacks it. Since warriors rotate between attacking and eating, the attack pressure stays high, and the Farm's wheat is used to keep spawning warriors until the 100 HP are depleted.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Village:
      - Hungry villagers (steps_since_meal >= 2) eat while wheat lasts.
      - Farmers are paired into 'spawn warrior' (12 wheat) when affordable,
        otherwise into 'spawn farmer' (10 wheat) if wheat is plentiful.
      - Warriors that have just eaten (steps_since_meal <= 1) go to the cave.
      - Everyone else farms.
    Cave:
      - Farmers return to the village.
      - Warriors with steps_since_meal < 3 attack; others return to eat.
    """

    HUNGRY_THRESHOLD = 2
    CAVE_ATTACK_LIMIT = 3  # attack only while steps_since_meal < 3

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        n = len(components)

        # Meal reserve: keep at least one wheat per villager for upcoming meals.
        reserve = n
        budget = wheat  # wheat that may be spent on meals and spawns

        assigned = {}

        # 1) Feeding: hungry villagers eat first, most starved first.
        hungry = sorted(
            [c for c in components if c.steps_since_meal >= self.HUNGRY_THRESHOLD],
            key=lambda c: c.steps_since_meal,
            reverse=True,
        )
        for c in hungry:
            if budget >= 1:
                assigned[id(c)] = "eat"
                budget -= 1
            else:
                # No food available: a starving villager cannot be saved by farming,
                # but we still keep it in the village.
                assigned[id(c)] = "eat"

        # 2) Spawning. Only farmers (who stay in the village) are used as spawn pairs.
        farmers_free = [
            c for c in components
            if c.role == "Farmer" and id(c) not in assigned
        ]
        spawn_w = 0
        spawn_f = 0

        # Warrior spawn: 2 farmers + 12 wheat, respecting the reserve.
        while len(farmers_free) >= 2 and budget - 12 >= reserve - len(hungry) and budget >= 12:
            a, b = farmers_free.pop(), farmers_free.pop()
            assigned[id(a)] = "spawn warrior"
            assigned[id(b)] = "spawn warrior"
            budget -= 12
            spawn_w += 1
            if spawn_w >= 2:  # limit spawns per step
                break

        # Farmer spawn with leftover wheat: 2 farmers + 10 wheat.
        while len(farmers_free) >= 2 and budget >= 10 + reserve and spawn_f < 1:
            a, b = farmers_free.pop(), farmers_free.pop()
            assigned[id(a)] = "spawn farmer"
            assigned[id(b)] = "spawn farmer"
            budget -= 10
            spawn_f += 1

        # 3) Warriors that have just eaten go to the cave.
        # 4) Everyone else farms.
        for c in components:
            if id(c) in assigned:
                continue
            if c.role == "Warrior" and c.steps_since_meal <= 1 and c.hp > 0:
                assigned[id(c)] = "cave"
            else:
                assigned[id(c)] = "farm"

        for c in components:
            environment.assign_group(c, assigned[id(c)])

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.role == "Farmer":
                # Farmers are not combat units; send them home to farm.
                environment.assign_group(c, "village")
            elif c.steps_since_meal >= self.CAVE_ATTACK_LIMIT:
                # Warrior nearing starvation: return to eat.
                environment.assign_group(c, "village")
            else:
                # Fed warrior: attack the Dragon (unless it is already dead).
                if environment.dragon.hp > 0:
                    environment.assign_group(c, "attack")
                else:
                    environment.assign_group(c, "cave")
```