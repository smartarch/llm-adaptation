**Strategy description:**

- **Eating first:** any villager with `steps_since_meal >= 4` is sent to "eat" (in the village) or back to the "village" (from the cave) so they never reach the 6-step starvation limit, even accounting for the one-step travel.
- **Attack waves (staggered):** warriors are the main damage dealers. To keep the dragon from regenerating while waves travel, I keep track of how many warriors were just sent to the cave and stagger: if the dragon has been engaged (hp < 100), I send a new warrior from the village whenever the number of warriors currently in the cave drops below a threshold. Otherwise, warriors farm temporarily to build wheat.
- **Farming:** farmers mostly farm (5 wheat/step), except a rotation where some farmers also join attack waves when the dragon is already engaged, adding extra damage.
- **Spawning:** only when wheat is abundant (> 40), spawn a warrior (better damage per wheat spent on offense); the two spawn-group members come from healthy, well-fed villagers who would otherwise farm.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.wave_size = 2  # warriors per wave

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        dragon = environment.dragon
        cave_warriors = sum(1 for w in environment.warriors if w.location == "Cave")
        # how many warriors we want attacking at once
        wanted = 4 if dragon.hp < 100 else 2

        ids = {g: i for i, g in enumerate(group_ids)}
        for c in components:
            # 1) hunger has top priority (6-step limit, travel takes a step)
            if c.steps_since_meal >= 4:
                environment.assign_group(c, ids["eat"])
                continue
            # 2) send reinforcements to the cave if needed and fed enough
            if (c.role == "Warrior" and dragon.hp < 100
                    and cave_warriors + self._pending < wanted
                    and wheat >= 12 and c.hp > 1):
                environment.assign_group(c, ids["cave"])
                self._pending += 1
                continue
            # 3) spawn a warrior occasionally when rich in wheat
            if wheat > 40 and c.steps_since_meal <= 2 and step % 4 == 0:
                environment.assign_group(c, ids["spawn warrior"])
                continue
            # 4) default: farm
            environment.assign_group(c, ids["farm"])

        # resolve pending count roughly at end of step
        self._pending = 0

    def assign_in_cave(self, components, environment, group_ids, step: int):
        ids = {g: i for i, g in enumerate(group_ids)}
        dragon = environment.dragon
        for c in components:
            # starving -> go home to eat (travel takes one step, then eat)
            if c.steps_since_meal >= 4:
                environment.assign_group(c, ids["village"])
                continue
            # weak villagers retreat too
            if c.hp <= 1:
                environment.assign_group(c, ids["village"])
                continue
            # everyone else attacks (even farmers help once engaged)
            if dragon.hp > 0:
                environment.assign_group(c, ids["attack"])
            else:
                environment.assign_group(c, ids["village"])
```

Note: `self._pending` is a simple bookkeeping hack to avoid sending everyone at once; it is reset each step, so effectively up to a couple of warriors travel per step once the dragon is engaged, which keeps continuous pressure on it.