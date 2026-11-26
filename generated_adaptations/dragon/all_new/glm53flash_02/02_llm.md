**Strategy description:**

- **In the Cave:** Any villager who is about to starve (`steps_since_meal >= 5`) returns to the Village so they can eat. Everyone else attacks the Dragon — the goal is to kill it fast, so we keep pressure on at all times.
- **In the Village:**
  - Villagers who are starving (`steps_since_meal >= 5`) go to the "eat" group first.
  - Warriors go to the "cave" group (they're the best attackers, and the Dragon has 100 HP, so rushing it is optimal).
  - Farmers farm to produce wheat (they're efficient there, 5 wheat per step).
  - If wheat is plentiful (>= 30), a couple of villagers are put into the "spawn farmer" / "spawn warrior" groups to grow the population, provided enough villagers remain to farm and feed the expedition. I keep spawning modest to avoid slowing the attack.

Everyone is always explicitly re-assigned, satisfying the "explicit re-assignment" rule.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _hungry(self, component):
        # 6 consecutive steps without eating => starvation; eat at 5 to be safe
        return component.steps_since_meal >= 5

    def assign_in_village(self, components, environment, group_ids, step: int):
        ids = {name: group_ids[i] for i, name in enumerate(group_ids)} \
            if not isinstance(group_ids, dict) else group_ids
        # robust mapping regardless of group_ids format
        gid = self._group_map(group_ids)

        wheat = environment.farm.wheat
        village_list = list(components)

        # count who will be doing what (preliminary)
        n_farm = sum(1 for c in village_list
                     if c.role == "Farmer" and not self._hungry(c))

        spawned = set()
        for c in village_list:
            if self._hungry(c):
                environment.assign_group(c, gid["eat"])
                spawned.add(c)
            elif c.role == "Warrior":
                environment.assign_group(c, gid["cave"])
                spawned.add(c)

        # remaining villagers (farmers) farm or spawn
        farmers = [c for c in village_list if c not in spawned]

        # decide spawning: keep enough farmers to feed everyone
        total_villagers = len(environment.warriors) + len(environment.farmers)
        spawn_budget = max(0, min(len(farmers) - 2, (wheat - 20) // 12))
        n_spawn = 0
        if wheat >= 34 and len(farmers) >= 3:
            # spawn warriors while we can afford them (2 per spawn + 12 wheat)
            n_spawn = min(2, spawn_budget)

        for i, c in enumerate(farmers):
            if i < n_spawn:
                environment.assign_group(c, gid["spawn warrior"])
            else:
                environment.assign_group(c, gid["farm"])

    def assign_in_cave(self, components, environment, group_ids, step: int):
        gid = self._group_map(group_ids)
        for c in components:
            if self._hungry(c):
                # go back to the village to eat
                environment.assign_group(c, gid["village"])
            else:
                environment.assign_group(c, gid["attack"])

    @staticmethod
    def _group_map(group_ids):
        if isinstance(group_ids, dict):
            return group_ids
        return {name: i for i, name in enumerate(group_ids)}
```