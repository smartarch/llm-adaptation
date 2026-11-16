## Adaptation strategy

The strategy separates the decisions that matter most for winning: keeping everyone fed, spawning reinforcements early, and keeping the Dragon under constant attack.

**In the Village (`assign_in_village`)**
1. **Eat first.** Any villager with `steps_since_meal >= 3` goes to the `eat` group, so nobody reaches the 6-step starvation limit. Each meal costs 1 wheat, so the wheat needed for these meals is reserved before any spawning.
2. **Spawn with the remaining wheat.** Farmers are used as spawners because warriors are needed in the Cave. A warrior is spawned first (12 wheat, two farmers in `spawn warrior`) to get at least two new warriors. If there is not enough wheat for a warrior, a farmer is spawned instead (10 wheat, two farmers in `spawn farmer`). Spawning only happens when enough wheat remains after reserving meals.
3. **Send fed warriors to the Cave.** Warriors with `steps_since_meal < 3` go to the `cave` group. Hungrier warriors stay behind to eat, as the optional recommendation asks.
4. **Farm everyone else.** All remaining farmers go to `farm`.

**In the Cave (`assign_in_cave`)**
1. **Retreat hungry villagers.** Any villager with `steps_since_meal >= 3` goes to `village`, so it can eat and return before it starves. Farmers in the Cave also go to `village`, since they must stay in the Village.
2. **Attack with healthy warriors.** Warriors with `steps_since_meal < 3` go to `attack`. Attacking every step keeps the Dragon from regenerating.
3. **Hold the rest.** Anyone else in the Cave stays in `cave`.

The Dragon is attacked from the first step a warrior arrives, which covers the "attacked within 15 steps" recommendation. The thresholds (3 steps for returning, 2 spawns in the Village) are chosen so that a warrior always has time to walk back, eat, and return before it starves. The code reads attributes with `getattr` defaults so it does not fail if an attribute is missing.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Strategy:
    - Village: feed hungry villagers first, spawn reinforcements (warriors preferred)
      with remaining wheat, send well-fed warriors to the Cave, farm with the rest.
    - Cave: attack with well-fed warriors, send hungry villagers and farmers back
      to the Village, keep the rest in the Cave.
    """

    HUNGER_EAT_THRESHOLD = 3    # village: eat when steps_since_meal >= 3
    HUNGER_RETURN_THRESHOLD = 3  # cave: go back to village when steps_since_meal >= 3
    WARRIOR_COST = 12
    FARMER_COST = 10

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _hunger(self, c):
        return getattr(c, "steps_since_meal", 0)

    def _role(self, c):
        return getattr(c, "role", "")

    def assign_in_village(self, components, environment, group_ids, step: int):
        comps = list(components)
        wheat = getattr(environment.farm, "wheat", 0)

        # 1. Feed hungry villagers first (each meal costs 1 wheat).
        hungry = [c for c in comps if self._hunger(c) >= self.HUNGER_EAT_THRESHOLD]
        eating_ids = set(id(c) for c in hungry)
        for c in hungry:
            environment.assign_group(c, "eat")
        wheat_after_meals = wheat - len(hungry)

        remaining = [c for c in comps if id(c) not in eating_ids]
        farmers = [c for c in remaining if self._role(c) == "Farmer"]
        warriors = [c for c in remaining if self._role(c) == "Warrior"]

        spawning_ids = set()

        # 2. Spawn with leftover wheat (spawners are farmers, to keep warriors free).
        if len(farmers) >= 2 and wheat_after_meals >= self.WARRIOR_COST:
            spawners = farmers[:2]
            for c in spawners:
                environment.assign_group(c, "spawn warrior")
                spawning_ids.add(id(c))
            wheat_after_meals -= self.WARRIOR_COST
        elif len(farmers) >= 2 and wheat_after_meals >= self.FARMER_COST:
            spawners = farmers[:2]
            for c in spawners:
                environment.assign_group(c, "spawn farmer")
                spawning_ids.add(id(c))
            wheat_after_meals -= self.FARMER_COST

        # 3. Send well-fed warriors to the Cave.
        for c in warriors:
            if self._hunger(c) < self.HUNGER_EAT_THRESHOLD:
                environment.assign_group(c, "cave")
                spawning_ids.add(id(c))  # mark as assigned

        # 4. Everyone else (farmers not spawning) farms; hungry warriors that
        #    were not eating (should not happen) go to farm too.
        for c in remaining:
            if id(c) in spawning_ids:
                continue
            environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            hunger = self._hunger(c)
            role = self._role(c)

            if role == "Farmer":
                # Farmers must stay in the Village.
                environment.assign_group(c, "village")
            elif hunger >= self.HUNGER_RETURN_THRESHOLD:
                # Hungry warrior: go back to eat before it starves.
                environment.assign_group(c, "village")
            else:
                # Healthy warrior: attack the Dragon.
                environment.assign_group(c, "attack")
```