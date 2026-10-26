

# Adaptation Strategy: SmartAdaptation

## Strategy Overview

The strategy balances three priorities:
1. **Aggression**: All warriors rush to the Cave and attack the Dragon immediately to deal 3 damage each per step.
2. **Economy**: Farmers produce wheat in the Village to fund spawning new units.
3. **Growth**: Periodically assign 2 farmers to spawn groups to create new warriors (for damage) and new farmers (for sustained wheat production).

### Village Phase Logic:
- **Warriors** → always sent to `"cave"` (satisfies "all warriors in cave" and "at least half warriors in cave").
- **Farmers**: Maintain at least 1-2 farmers farming (depending on total count). Excess farmers (in pairs) go to `"spawn warrior"` during early-mid game (steps 0-12), and occasionally to `"spawn farmer"` to sustain the economy. Remaining farmers → `"farm"`.

### Cave Phase Logic:
- **Warriors** → `"attack"` (all warriors attack the Dragon every step they're in the cave).
- **Non-warriors** (farmers that somehow ended up in cave) → sent back to `"village"`.

This ensures the Dragon (50 HP) takes 3 damage per warrior per step, giving ~4-5 warriors roughly 4 steps to kill it, well within the 30-step limit while allowing time for spawning.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._warrior_spawns = 0
        self._farmer_spawns = 0

    def assign_in_village(self, components, environment, group_ids, step):
        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        wheat = environment.farm.wheat

        # All warriors go to the cave to attack the Dragon
        for w in warriors:
            environment.assign_group(w, "cave")

        # Determine how many farmers must stay farming (economy floor)
        if len(farmers) >= 4:
            min_farming = 2
        else:
            min_farming = 1

        available_for_spawn = max(0, len(farmers) - min_farming)

        # Decide whether to spawn this step
        spawn_group = None
        num_spawn = 0

        # Priority 1: Spawn warriors in early-mid game for damage output
        if step < 12 and wheat >= 12 and available_for_spawn >= 2 and self._warrior_spawns < 4:
            spawn_group = "spawn warrior"
            num_spawn = 2
        # Priority 2: Spawn farmers to grow wheat production (at least a few)
        elif step >= 2 and wheat >= 10 and available_for_spawn >= 2 and self._farmer_spawns < 3:
            spawn_group = "spawn farmer"
            num_spawn = 2
        # Priority 3: Later spawning if we still have excess farmers and wheat
        elif step < 22 and wheat >= 12 and available_for_spawn >= 2 and self._warrior_spawns < 6:
            spawn_group = "spawn warrior"
            num_spawn = 2

        # Assign farmers to groups
        for i, farmer in enumerate(farmers):
            if spawn_group and i < num_spawn:
                environment.assign_group(farmer, spawn_group)
            else:
                environment.assign_group(farmer, "farm")

        # Track spawns for limiting total number
        if spawn_group == "spawn warrior":
            self._warrior_spawns += 1
        elif spawn_group == "spawn farmer":
            self._farmer_spawns += 1

    def assign_in_cave(self, components, environment, group_ids, step):
        for c in components:
            if c.role == "Warrior":
                # All warriors attack the Dragon
                environment.assign_group(c, "attack")
            else:
                # Non-warriors (farmers) should return to village
                environment.assign_group(c, "village")
```

### Key Design Decisions:
- **Warriors never retreat**: They always go to the cave and always attack, ensuring maximum DPS and satisfying the requirement that all warriors attack.
- **Staggered spawning**: Warriors are spawned first (steps 0-12) for immediate damage impact, then farmers are spawned to sustain the wheat economy, with additional warriors spawned later if resources allow.
- **Minimum farming guarantee**: At least 1-2 farmers always produce wheat, preventing economic collapse.
- **Cave cleanup**: Any non-warriors in the cave are sent back to the village, ensuring the cave group stays focused on attacking.