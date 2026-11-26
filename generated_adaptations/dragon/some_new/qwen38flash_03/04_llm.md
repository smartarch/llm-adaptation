

Looking at the test failures, I see two main issues:
1. **Dragon not killed**: Too few warriors attacking, and not enough replacement warriors spawned after deaths
2. **Spawning issues**: Not aggressively spawning warriors/farmers when villager count is low
3. **Eating/deployment interaction**: Warriors sent to cave with high `s_m` arrive at the boundary and immediately need to leave

**Strategy redesign:**
- Aggressively spawn warriors using farmer pairs whenever wheat allows (especially when < 5 villagers or 0 warriors)
- Only send warriors to cave when `s_m <= 1` so they arrive with enough time to attack
- In cave, attack until `s_m >= 4`, then return to village
- In village, eat at `s_m >= 4`, farm otherwise
- Keep spawning to replace dead warriors; use any 2 villagers for spawn pairs if farmers are scarce

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step):
        if not components:
            return

        wheat = environment.farm.wheat
        all_farmers = [f for f in environment.farmers if f.hp > 0]
        all_warriors = [w for w in environment.warriors if w.hp > 0]
        total_villagers = len(all_farmers) + len(all_warriors)
        total_warriors_alive = len(all_warriors)

        # 1) Eating: s_m >= 4 must eat in village (s_m never reaches 6)
        eat_ids = set()
        for c in components:
            if c.steps_since_meal >= 4:
                environment.assign_group(c, "eat")
                eat_ids.add(id(c))

        remaining = [c for c in components if id(c) not in eat_ids]
        v_farmers = [c for c in remaining if c.role == "Farmer"]
        v_warriors = [c for c in remaining if c.role == "Warrior"]

        # 2) Spawning decisions
        reserve = total_villagers  # 1 meal reserve per villager
        spawn_pool = v_farmers

        need_warrior = (total_warriors_alive == 0
                        or total_villagers < 5
                        or total_warriors_alive < 4)
        need_farmer = (total_villagers < 5 and len(all_farmers) < 4)

        spawn_done = False
        used_ids = set()

        if need_warrior and wheat >= 12 + reserve and len(spawn_pool) >= 2:
            environment.assign_group(spawn_pool[0], "spawn warrior")
            environment.assign_group(spawn_pool[1], "spawn warrior")
            used_ids = {id(spawn_pool[0]), id(spawn_pool[1])}
            spawn_done = True
        elif need_farmer and wheat >= 10 + reserve and len(spawn_pool) >= 2:
            environment.assign_group(spawn_pool[0], "spawn farmer")
            environment.assign_group(spawn_pool[1], "spawn farmer")
            used_ids = {id(spawn_pool[0]), id(spawn_pool[1])}
            spawn_done = True
        elif need_warrior and wheat >= 12 + reserve and len(v_warriors) >= 2:
            # Fallback: use warriors as spawn pair (they aren't consumed)
            environment.assign_group(v_warriors[0], "spawn warrior")
            environment.assign_group(v_warriors[1], "spawn warrior")
            used_ids = {id(v_warriors[0]), id(v_warriors[1])}
            spawn_done = True

        v_farmers = [c for c in v_farmers if id(c) not in used_ids]
        v_warriors = [c for c in v_warriors if id(c) not in used_ids]

        # 3) Remaining farmers → farm
        for c in v_farmers:
            environment.assign_group(c, "farm")

        # 4) Warriors: go to cave only if s_m <= 1 (arrive with s_m<=2, can attack 2-3 turns)
        #    Higher s_m → farm in village first, eat, then deploy next cycle
        for c in v_warriors:
            if c.steps_since_meal <= 1:
                environment.assign_group(c, "cave")
            else:
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        if not components:
            return

        for c in components:
            if c.steps_since_meal >= 4:
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")
```