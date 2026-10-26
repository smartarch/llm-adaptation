

## Analysis of Failure

The 0% win rate reveals a critical bug in my spawning logic: the condition `(len(farmers) - idx) >= 4` requires at least **2 farmers to spawn + 2 to farm = 4 farmers total**, which is impossible with a small starting population. I could never spawn anything. Additionally, I wasn't handling the case where farmers are too few, and I wasn't protecting damaged villagers in the cave.

## New Strategy

1. **Warriors go to cave immediately** and attack every turn.
2. **Farmers farm** to build up wheat. No spawning until we have enough resources and enough spare farmers.
3. **Spawn only when affordable**: Need ≥12 wheat AND at least 3 farmers (2 to spawn + 1 to keep farming). Spawn warriors first (offensive priority), then farmers.
4. **Protect villagers**: If HP ≤ 1 in the cave, send them back to village to avoid death.
5. **No unnecessary waiting**: Attack from step 1. Keep farming tight.

```py
import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.warriors_spawned = 0
        self.farmers_spawned = 0
        self.target_warriors = 5   # total warriors on field (incl. starting)
        self.target_farmers = 4    # total farmers on field (incl. starting)

    def assign_in_village(self, components, environment, group_ids, step: int):
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]
        wheat = environment.farm.wheat

        # All warriors go to the cave immediately
        for w in warriors:
            environment.assign_group(w, "cave")

        n_farmers = len(farmers)
        if n_farmers == 0:
            return

        # Determine whether we need more warriors or farmers
        # We can only spawn if we have at least 3 farmers (2 for spawn + 1 farming)
        can_spawn = n_farmers >= 3

        need_warriors = self.warriors_spawned < 3  # spawn up to 3 extra warriors
        need_farmers = self.farmers_spawned < 2    # spawn up to 2 extra farmers

        spawned_this_step = False

        # Priority 1: Spawn a warrior (offensive priority)
        if can_spawn and need_warriors and wheat >= 12:
            environment.assign_group(farmers[0], "spawn warrior")
            environment.assign_group(farmers[1], "spawn warrior")
            self.warriors_spawned += 1
            spawned_this_step = True
            # Remaining farmers go to farm
            for i in range(2, n_farmers):
                environment.assign_group(farmers[i], "farm")
            return

        # Priority 2: Spawn a farmer (economy, only a couple needed)
        if can_spawn and not need_warriors and need_farmers and wheat >= 10:
            environment.assign_group(farmers[0], "spawn farmer")
            environment.assign_group(farmers[1], "spawn farmer")
            self.farmers_spawned += 1
            spawned_this_step = True
            for i in range(2, n_farmers):
                environment.assign_group(farmers[i], "farm")
            return

        # Default: all farmers go to the farm
        for f in farmers:
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.role == "Warrior":
                if c.hp <= 1:
                    # Too weak, send back to village to avoid death
                    environment.assign_group(c, "village")
                else:
                    environment.assign_group(c, "attack")
            elif c.role == "Farmer":
                if c.hp <= 1:
                    environment.assign_group(c, "village")
                else:
                    # Farmers in cave: they deal 1 dmg, might as well attack
                    # but prefer to send them back if we have enough warriors
                    environment.assign_group(c, "village")
```