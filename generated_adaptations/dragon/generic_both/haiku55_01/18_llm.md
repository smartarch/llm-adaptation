## Analysis of the previous attempt

Ten variants have scored 0%, so I can't pin the failure to one parameter. The logs I have don't show the Dragon's HP trajectory or the army size over time, so I'm working from the rules rather than from observed failures. Three points stand out:

1. **Waiting costs time.** The batch-strike versions spent steps 0 to 10 idle in the Cave. Because the Dragon only counterattacks when attacked, waiting is safe, but it leaves little time for 17 or more warrior hits within 30 steps.
2. **Economy growth was too weak.** Farmers are the only real wheat source (5 per step, versus 2 for warriors). Warriors built early produce little, and a farmer pays back its 10-wheat cost within about two steps, so the first few steps should go to farmers.
3. **Spawn thresholds were rigid.** Fixed counts such as "at least 4 farmers" or "strike at 4 warriors" sometimes left wheat idle or delayed the fight.

## Revised strategy: economy first, then continuous warrior output

- **Warriors** go to `"cave"` as soon as they exist and attack every step. This gives the earliest possible damage and satisfies the first-15-steps requirement without a waiting phase.
- **Farmers** never leave the Village. Three always stay on `"farm"`.
- **Economy phase:** While there are fewer than 6 farmers, the spare farmers are paired and spawned as farmers (10 wheat per pair).
- **Army phase:** Once the farmer count reaches 6, spare farmers are paired and spawned as warriors (12 wheat per pair), so wheat keeps converting into damage.
- **Cave:** Farmers that end up there are sent back to `"village"`.

This is an untested adjustment. It moves the economy-to-army switch to a farmer-count threshold and removes the strike delay. I can't guarantee it will win, because the outcome depends on the unseen initial villager counts and spawn timing.

```py
import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Economy first, then continuous warrior production.
    - Warriors go to the Cave immediately and attack every step.
    - Three farmers always stay on the farm.
    - While fewer than 6 farmers exist, spare farmers are paired and spawn
      farmers (10 wheat). After that, spare farmers spawn warriors (12 wheat).
    - Farmers never enter the Cave.
    """

    WARRIOR_SPAWN_COST = 12
    FARMER_SPAWN_COST = 10
    RESERVE_FARMERS = 3
    FARMER_TARGET = 6

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat

        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        # Warriors head straight to the Cave.
        for w in warriors:
            environment.assign_group(w, "cave")

        # Reserve farmers that keep producing wheat.
        reserve = min(self.RESERVE_FARMERS, len(farmers))
        farming = farmers[:reserve]
        available = farmers[reserve:]

        spawn_farmer = []
        spawn_warrior = []

        if len(farmers) < self.FARMER_TARGET:
            # Economy phase: grow the farmer population.
            while len(available) >= 2 and wheat >= self.FARMER_SPAWN_COST:
                spawn_farmer.extend(available[:2])
                available = available[2:]
                wheat -= self.FARMER_SPAWN_COST
        else:
            # Army phase: convert spare farmers into warriors.
            while len(available) >= 2 and wheat >= self.WARRIOR_SPAWN_COST:
                spawn_warrior.extend(available[:2])
                available = available[2:]
                wheat -= self.WARRIOR_SPAWN_COST

        # Anyone left over keeps farming.
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
                # Farmers never fight; send them back to the Village.
                environment.assign_group(c, "village")
```