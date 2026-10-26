

Looking at the simulation results, the Dragon's HP never decreased in any game, meaning **no attacks ever landed**. This suggests that either warriors never make it to the cave/attack state, or no warriors are ever created. Let me diagnose and fix the issues:

**Problems identified:**
1. Instance variables (`self.warriors_spawned`, etc.) persist across games in the same simulation session, causing spawn logic to break after the first game.
2. The spawn thresholds and step-based gating were too conservative — if we start with only farmers, we never accumulate enough wheat to spawn warriors quickly enough.
3. The overall logic was too cautious. I need to be extremely aggressive about getting any warrior into attack position.

**New strategy:**
- Remove all persistent state — use only step/wheat-based decisions (stateless per turn).
- Send warriors to cave IMMEDIATELY (no delay).
- Spawn warriors as soon as wheat allows (no step gating beyond step 0).
- In cave: warriors ALWAYS attack.
- Keep spawning logic simple: if we have ≥2 farmers and enough wheat, spawn.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step):
        wheat = environment.wheat
        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        # CRITICAL: All warriors go to cave immediately to attack
        for w in warriors:
            environment.assign_group(w, "cave")

        # Determine spawning: be very aggressive
        # We need at least 2 farmers in the spawn group to spawn one unit.
        # Prioritize warrior spawning (3 dmg) over farmer spawning (farming).
        # Keep at least 2 farmers farming to build wheat for future spawns.
        
        remaining_farmers = list(farmers)
        spawned_this_turn = False

        # Try to spawn a warrior first (most impactful for damage)
        if not spawned_this_turn and len(remaining_farmers) >= 2 and wheat >= 12:
            # Only spawn warrior if we have a buffer (keep at least 2 farmers farming next turn)
            # or if we have plenty of wheat (economy won't suffer)
            buffer_after_spawn = wheat - 12
            if len(remaining_farmers) >= 4 or buffer_after_spawn >= 4:
                environment.assign_group(remaining_farmers[0], "spawn warrior")
                environment.assign_group(remaining_farmers[1], "spawn warrior")
                remaining_farmers = remaining_farmers[2:]
                spawned_this_turn = True

        # Try to spawn a farmer second (grows economy)
        if not spawned_this_turn and len(remaining_farmers) >= 2 and wheat >= 10:
            # Spawn farmer if we have enough buffer and plenty of wheat
            if len(remaining_farmers) >= 4 or (wheat - 10) >= 4:
                environment.assign_group(remaining_farmers[0], "spawn farmer")
                environment.assign_group(remaining_farmers[1], "spawn farmer")
                remaining_farmers = remaining_farmers[2:]
                spawned_this_turn = True

        # All remaining farmers farm
        for f in remaining_farmers:
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        for c in components:
            if c.role == "Warrior":
                # Warriors attack the dragon every single turn they are in the cave
                environment.assign_group(c, "attack")
            else:
                # Non-warriors should return to the village
                environment.assign_group(c, "village")
```

The key changes:
1. **No persistent state** — completely stateless per turn, so it works correctly across multiple games.
2. **Immediate warrior deployment** — zero delay sending warriors to cave.
3. **Simpler spawn logic** — just check wheat ≥ cost and enough farmers available.
4. **Aggressive spawning** — spawn as soon as wheat allows without artificial step delays.