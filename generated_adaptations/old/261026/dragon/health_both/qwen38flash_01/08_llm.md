

# Analysis

After three failed attempts with different strategies, the Dragon HP **never** drops from 50 at any step. This means no component ever successfully attacks. Possible root causes:

1. **Role detection may fail** — `c.role` might return lowercase `"warrior"` or a different format, causing my `if c.role == "Warrior"` checks to silently fail, so no one gets assigned to `"attack"`.
2. **Spawning never triggers** — if initial wheat is very low and there are few farmers, my thresholds are never met.
3. **Too many conditional branches** — each one is a potential failure point where a component falls through without any assignment.

# New Strategy: Minimal, Unconditional, Aggressive

- **Remove ALL role-checking**. In the village, send **everything** to `"cave"`. In the cave, assign **everything** to `"attack"`. This guarantees that whatever exists will deal damage (farmers=1 dmg, warriors=3 dmg).
- **No spawning complexity** — just farm when it makes sense, but the priority is getting bodies into the attack loop immediately.
- **Keep 2 farmers farming** only if we have more than 2 total; otherwise everyone attacks.
- **One turn of farming** at step 0 to get wheat, then everything storms the cave.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step):
        wheat = environment.wheat
        n = len(components)

        if n == 0:
            return

        # Be extremely aggressive: almost everyone goes to cave to attack.
        # Only keep a couple farmers to farm if we have plenty and wheat is low.
        # But never delay attacks past step 2.

        should_farm = (
            step <= 1
            and wheat < 6
            and n >= 3
        )

        if should_farm:
            # Keep up to 2 for farming, rest go to cave
            farm_count = min(2, n - 1)
            for i in range(farm_count):
                environment.assign_group(components[i], "farm")
            for i in range(farm_count, n):
                environment.assign_group(components[i], "cave")
        elif wheat >= 12 and n >= 4:
            # Occasionally spawn using 2 farmers (try every few turns)
            if step % 4 == 0:
                environment.assign_group(components[0], "spawn warrior")
                environment.assign_group(components[1], "spawn warrior")
                for i in range(2, n):
                    environment.assign_group(components[i], "cave")
            else:
                # Everyone goes to cave
                for c in components:
                    environment.assign_group(c, "cave")
        else:
            # SEND EVERYTHING TO CAVE - attack now!
            for c in components:
                environment.assign_group(c, "cave")

    def assign_in_cave(self, components, environment, group_ids, step):
        # NO role checking - assign EVERYONE in cave to attack
        # This handles cases where role string may differ from expected
        for c in components:
            environment.assign_group(c, "attack")
```

The critical change: **`assign_in_cave` no longer checks `c.role`**. Every component in the cave is unconditionally assigned to `"attack"`. If the role string was mismatched (e.g., lowercase), this bypasses the bug entirely. Similarly, in `assign_in_village`, almost everything goes to `"cave"` regardless of role, ensuring no component gets "stuck" due to a role detection failure.