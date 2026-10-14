## Analysis of the previous attempt

Every version so far has sent warriors to fight as soon as they existed. That causes two problems:

1. **Counterattacks only happen when the Dragon is attacked.** Each attack round, every villager in the Cave has a 40% chance to take 1 damage, and each round has a 20% chance of eating one villager. A warrior with 6 HP can survive only about 15 rounds on average, so a trickle of warriors arriving one at a time gets worn down while the Dragon is still healthy.
2. **Trickling in is inefficient.** Each round in the Cave exposes everyone there to the Dragon's counterattack. Dealing the same total damage in fewer rounds means fewer counterattacks.

## Revised strategy: build up, then strike in one batch

**Village phase:**
- Warriors wait in the Village on `"farm"`, so they still produce wheat (2 each) while the army builds.
- Farmers are converted into warriors with wheat as it becomes available. Two farmers form a pair, and each pair spawns a warrior for 12 wheat. At least 2 farmers always stay on `"farm"`. If the farmer count drops below 4, a pair is spawned as a farmer instead (10 wheat) to rebuild the economy.

**Strike decision:**
- Once the Village holds at least 3 warriors, or step 8 is reached, the strike is triggered. This is a one-way switch.
- After the strike, all warriors go to `"cave"` and attack every step. New warriors join the strike immediately. The first attack therefore happens by step 8 or earlier, which satisfies the first-15-steps requirement.

**Cave phase:**
- Warriors attack every step.
- Farmers that reach the Cave are sent back to `"village"`, except when the Dragon is at 15 HP or less, when they join the final push.

**Why this should help:** A group of about 4 warriors deals 12 damage per round, so the Dragon falls in about 5 rounds. That gives far less exposure than a slow trickle, and the wheat income from the farm continues during the build-up.

```py
import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Build up an army in the Village, then strike in one batch.
    - Warriors farm while the army is being assembled.
    - Farmers are converted into warriors (pairs, 12 wheat) while keeping
      at least two farmers working; farmers are rebuilt when too few remain.
    - The strike starts once >=3 warriors are ready or step >= 8. After that,
      all warriors go to the Cave and attack every step, so the Dragon takes
      damage early and in few rounds (fewer counterattacks).
    - Farmers join the attack only in the final push (Dragon HP <= 15).
    """

    WARRIOR_SPAWN_COST = 12
    FARMER_SPAWN_COST = 10
    MIN_FARMING = 2
    MIN_FARMERS = 4
    STRIKE_WARRIORS = 3
    STRIKE_STEP = 8
    FINAL_PUSH_HP = 15

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.strike = False

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat

        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        # Decide whether to start the strike (one-way switch).
        if not self.strike and (len(warriors) >= self.STRIKE_WARRIORS or step >= self.STRIKE_STEP):
            self.strike = True

        # Warriors: fight once the strike is on, otherwise farm while building up.
        for w in warriors:
            environment.assign_group(w, "cave" if self.strike else "farm")

        # Keep a minimal farming core.
        reserve = min(self.MIN_FARMING, len(farmers))
        farming = farmers[:reserve]
        available = farmers[reserve:]

        spawn_warrior = []
        spawn_farmer = []

        # Rebuild the farmer economy if too few farmers remain.
        if len(farmers) < self.MIN_FARMERS:
            while len(available) >= 2 and wheat >= self.FARMER_SPAWN_COST:
                spawn_farmer.extend(available[:2])
                available = available[2:]
                wheat -= self.FARMER_SPAWN_COST

        # Convert the rest into warriors while wheat allows.
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
        dragon_hp = environment.dragon.hp
        final_push = dragon_hp <= self.FINAL_PUSH_HP

        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            elif final_push:
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```