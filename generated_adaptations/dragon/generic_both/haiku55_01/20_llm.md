## Analysis of the previous attempt

Eleven variants have scored 0%, and the logs I have don't show Dragon HP, army size, or wheat over time, so I can't identify the failure precisely. The rules suggest a few likely problems:

1. **Fixed reserves are a poor fit.** Earlier versions used fixed numbers of farmers on the farm (1, 2, 3) and fixed farmer targets. The right split depends on how much wheat is on hand and how many farmers are available.
2. **Idle wheat wastes tempo.** Wheat only helps once it becomes warriors. Versions that waited, or that built farmers before warriors, left wheat unspent while the 30-step clock ran.
3. **Warriors need to attack at once.** Waiting in the Cave is safe, but it delays damage. Since 50 HP needs about 17 warrior hits, every idle step counts.

## Revised strategy: adaptive reserve, immediate attacks

- **Warriors** go to `"cave"` as soon as they exist and attack every step. The Dragon only counterattacks when attacked, so this costs nothing extra.
- **Farmers** never leave the Village. The number kept on `"farm"` is adaptive. It is the number needed to keep income ahead of the spawn cost, with a floor of 1. Spawning is sized from the wheat on hand, and the spare farmers are spent on warriors (12 wheat per pair).
- **Farmer rebuild:** If the total farmer count falls below 3, spare pairs spawn farmers (10 wheat) before warriors. Farmers are the only real wheat source, so losing them stalls everything.
- **Cave:** Any farmer that ends up there is sent back to `"village"`.

This is an untested adjustment. The outcome still depends on the unseen starting army and spawn mechanics, so I can't promise a win.

```py
import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Adaptive-reserve strategy with immediate warrior attacks.
    - Warriors go to the Cave and attack every step.
    - Farmers never enter the Cave. The number kept farming adapts to the
      current farmer count, with a floor of one.
    - If fewer than 3 farmers exist, spare pairs spawn farmers (10 wheat).
    - Otherwise spare pairs spawn warriors (12 wheat) while wheat allows.
    """

    WARRIOR_SPAWN_COST = 12
    FARMER_SPAWN_COST = 10
    MIN_FARMERS = 3

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat

        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        for w in warriors:
            environment.assign_group(w, "cave")

        n = len(farmers)
        # Adaptive reserve: about one farmer in three keeps farming, floor of one.
        reserve = min(n, max(1, n // 3))
        farming = farmers[:reserve]
        available = farmers[reserve:]

        spawn_farmer = []
        spawn_warrior = []

        if n < self.MIN_FARMERS:
            # Rebuild the wheat economy first.
            while len(available) >= 2 and wheat >= self.FARMER_SPAWN_COST:
                spawn_farmer.extend(available[:2])
                available = available[2:]
                wheat -= self.FARMER_SPAWN_COST
        else:
            # Convert spare farmers into warriors while wheat allows.
            while len(available) >= 2 and wheat >= self.WARRIOR_SPAWN_COST:
                spawn_warrior.extend(available[:2])
                available = available[2:]
                wheat -= self.WARRIOR_SPAWN_COST

        farming.extend(available)

        for f in spawn_farmer:
            environment.assign_group(f, "spawn farmer")
        for f in spawn_warrior:
            environment.assign_group(f, "spawn warrior")
        for f in farming:
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```