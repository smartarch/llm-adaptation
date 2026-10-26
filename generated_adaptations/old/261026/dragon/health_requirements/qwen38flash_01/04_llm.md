

# Analysis and Improved Strategy

## Root Cause Analysis

Looking at the game logs:
- **Game 1**: Only 1 warrior (3 dmg/step), died quickly, no warriors spawned after. Dragon stuck at 35 HP.
- **Game 2**: ~1-2 warriors, died partway through. Dragon stuck at 17 HP.
- **Game 3**: 1 warrior, died after 2 steps. Dragon stuck at 44 HP.

The core problems were:
1. **Spawn logic required `available_for_spawn >= 2`** but with only 2 starting farmers and `min_farming = 1`, we could never form a spawn pair.
2. **Not enough warriors spawned** — the Dragon needs sustained DPS. With 1 warrior dying in ~5 steps, we deal ~15 damage before losing all attackers.
3. **Need 4-5 warriors attacking simultaneously** to kill 50 HP before they all die (eat kills at any HP).

## Improved Strategy

1. **Aggressive warrior spawning**: Every step, if we have ≥2 farmers AND ≥12 wheat, use 2 farmers to spawn a warrior. Otherwise ALL farmers farm.
2. **All warriors → cave → attack** (as required). No holding back.
3. **Slightly stagger**: Alternate between "all farmers farm" and "2 farmers spawn warrior" to maintain wheat flow.
4. **In cave**: All warriors attack. If HP ≤ 1, send back to village (they'll die next attack anyway from AoE, so let them produce 2 wheat instead).
5. **After initial warriors built up**, occasionally spawn farmers to sustain wheat production.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step):
        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        wheat = environment.farm.wheat

        # All warriors go to the cave to attack
        for w in warriors:
            environment.assign_group(w, "cave")

        # Decide spawning strategy
        # Priority: spawn warriors aggressively early to build attack force
        spawned = False
        farmers_assigned = 0

        # Try to spawn a warrior every step if we can
        if len(farmers) >= 2 and wheat >= 12:
            # Assign 2 farmers to spawn warrior
            for i in range(min(2, len(farmers))):
                environment.assign_group(farmers[i], "spawn warrior")
            farmers_assigned = 2
            spawned = True
        elif len(farmers) >= 4 and wheat >= 10 and step >= 8:
            # Later in game, spawn farmers to boost economy
            for i in range(2):
                environment.assign_group(farmers[i], "spawn farmer")
            farmers_assigned = 2
            spawned = True

        # Remaining farmers go to farm
        for i in range(farmers_assigned, len(farmers)):
            environment.assign_group(farmers[i], "farm")

        # If we have 0 farmers (shouldn't happen), handle edge case
        # If there are no farmers at all, warriors already handled above

    def assign_in_cave(self, components, environment, group_ids, step):
        for c in components:
            if c.role == "Warrior":
                if c.hp <= 1:
                    # Send very low HP warriors back to village to avoid
                    # wasting them (they can produce wheat instead)
                    # They'd likely die next AoE tick anyway
                    environment.assign_group(c, "village")
                else:
                    # All healthy warriors attack the Dragon
                    environment.assign_group(c, "attack")
            else:
                # Non-warriors in cave go back to village
                environment.assign_group(c, "village")
```

### Key Changes from Previous Version:
1. **Removed the `min_farming` threshold** — if we have 2+ farmers and enough wheat, we ALWAYS spawn a warrior. No more "can never form a pair" bug.
2. **Aggressive warrior spawning** — try to spawn a warrior EVERY step (not just every few steps).
3. **Low-HP warrior retreat** — warriors with HP≤1 go back to village instead of getting one-shotted by AoE. They contribute 2 wheat until a healthier unit replaces them.
4. **Simpler logic** — fewer conditions, more aggressive action. The Dragon's 50 HP requires ~4-5 simultaneous attackers; this strategy builds that force as fast as wheat allows.