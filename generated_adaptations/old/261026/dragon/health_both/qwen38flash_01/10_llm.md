

# Deep Analysis

After 4 failed attempts, the Dragon HP **never** drops by even 1 point across all 90 turns. This is impossible if any warrior ever attacks. The problem must be more fundamental:

1. Maybe the group names I'm using don't match what's actually available (the `group_ids` parameter tells me valid names).
2. Maybe components never reach the cave, or never appear in the cave's component list.
3. Maybe the assignment syntax or group naming convention differs from what I assumed.

# New Approach: Use `group_ids` Directly

I'll use the actual `group_ids` list passed by the environment to determine valid groups, rather than hardcoding names. I'll also make the logic as simple as possible — no conditionals, no role checks, no spawning. Just get bodies to attack.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step):
        if not components:
            return

        # Find the group that sends units to the cave
        cave_group = None
        for g in group_ids:
            if "cave" in g.lower():
                cave_group = g
                break

        if cave_group is None and group_ids:
            cave_group = group_ids[0]

        if cave_group is None:
            return

        # After step 3, send ALL components to cave.
        # First 3 steps: farm a bit to build wheat, send half to cave.
        if step <= 2 and len(components) >= 2:
            half = len(components) // 2
            for i, c in enumerate(components):
                if i < half:
                    # Try to find farm group
                    farm_group = None
                    for g in group_ids:
                        if "farm" in g.lower():
                            farm_group = g
                            break
                    if farm_group:
                        environment.assign_group(c, farm_group)
                    else:
                        environment.assign_group(c, cave_group)
                else:
                    environment.assign_group(c, cave_group)
        else:
            # Send EVERYTHING to cave to attack
            for c in components:
                environment.assign_group(c, cave_group)

    def assign_in_cave(self, components, environment, group_ids, step):
        if not components:
            return

        # Find the attack group from the available groups
        attack_group = None
        for g in group_ids:
            if "attack" in g.lower():
                attack_group = g
                break

        if attack_group is None and group_ids:
            attack_group = group_ids[0]

        if attack_group is None:
            return

        # Assign EVERYTHING to attack. No exceptions.
        for c in components:
            environment.assign_group(c, attack_group)
```

The key differences from previous attempts:
- **Uses `group_ids`** to discover actual valid group names instead of hardcoding "attack"/"cave"
- **Case-insensitive matching** for group name discovery
- **Sends half to cave immediately** in first 3 steps (previously everyone farmed)
- **After step 2, EVERYTHING goes to cave** regardless of role
- **Zero role checking** — all components in cave get assigned to attack group