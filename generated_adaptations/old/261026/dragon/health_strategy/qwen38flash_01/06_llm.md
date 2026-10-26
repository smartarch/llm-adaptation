

## Analysis of Failures

**Game 1**: Dragon stalls at 35 HP — single warrior died, no replacements spawned.
**Game 2**: Stalls at 17 HP — same issue, warrior pipeline dried up.
**Game 3**: Stalls at 44 HP — warrior died after 2 steps, nothing spawned.

**Root cause**: My `MIN_FARMING = 2` constraint in the spawning loop required having **4+ farmers** (`len >= 2 + MIN_FARMING`) before ANY spawning could happen. With 2-3 starting farmers, **zero warriors were ever spawned**. The spawning code was completely dead.

**Fix**: 
1. Remove the over-restrictive constraint. Use 2 farmers to spawn, the rest farm.
2. Spawn warriors aggressively — as soon as 2 farmers + 12 wheat are available.
3. The 2 farmers assigned to "spawn warrior" return next step to farm, so we don't lose them permanently.
4. Limit farmer spawns to 1 extra to boost wheat output slightly without wasting wheat.
5. Warriors in cave always attack — no retreat.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.spawned_farmers = 0
        self.total_villagers_seen = 0

    def assign_in_village(self, components, environment, group_ids, step):
        wheat = environment.farm.wheat

        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # All warriors in village go to cave immediately
        for w in warriors:
            environment.assign_group(w, "cave")

        remaining_farmers = list(farmers)

        # Phase 1: Spawn at most 1 extra farmer early to boost wheat production
        # Need 2 farmers + 10 wheat. After spawning, those 2 return to farm next step.
        if self.spawned_farmers < 1 and len(remaining_farmers) >= 2 and wheat >= 10:
            environment.assign_group(remaining_farmers[0], "spawn farmer")
            environment.assign_group(remaining_farmers[1], "spawn farmer")
            remaining_farmers = remaining_farmers[2:]
            wheat -= 10
            self.spawned_farmers += 1

        # Phase 2: Aggressively spawn warriors — this is our damage pipeline
        # Each warrior costs 2 farmers (busy this step) + 12 wheat
        # Those 2 farmers return to farming next step
        while len(remaining_farmers) >= 2 and wheat >= 12:
            environment.assign_group(remaining_farmers[0], "spawn warrior")
            environment.assign_group(remaining_farmers[1], "spawn warrior")
            remaining_farmers = remaining_farmers[2:]
            wheat -= 12

        # Phase 3: All remaining farmers produce wheat
        for f in remaining_farmers:
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        for c in components:
            if c.role == "Warrior":
                # Warriors deal 3 damage — always attack, never retreat
                environment.assign_group(c, "attack")
            else:
                # Farmers don't belong in cave; send back to village to farm
                environment.assign_group(c, "village")
```