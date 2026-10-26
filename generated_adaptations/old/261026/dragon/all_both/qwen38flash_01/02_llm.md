

Looking at this problem, I need to design a strategy that:
1. Sends all warriors to the cave immediately to attack the dragon
2. Keeps farmers in the village to produce wheat and spawn new villagers
3. Alternates spawning warriors and farmers to sustain the army
4. Ensures the dragon is attacked early (within first 15 steps)

**Strategy:**
- **In village:** Warriors are immediately dispatched to the cave. Farmers either farm wheat or are used for spawning (alternating between warriors and farmers to build up both types). We spawn when wheat is sufficient and we can spare 2 farmers.
- **In cave:** Warriors continuously attack the dragon. Any stray farmers get sent back to village.

```py
import math
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._spawn_counter = 0  # Track alternation between warrior/farmer spawns

    def assign_in_village(self, components, environment, group_ids, step: int):
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]
        wheat = environment.farm.wheat

        # All warriors in village must go to the cave immediately
        for w in warriors:
            environment.assign_group(w, "cave")

        # Farmer strategy: farm or spawn
        remaining_farmers = list(farmers)

        # Determine if we should spawn this step
        # We need at least 2 farmers to be useful for farming next round
        # Prioritize warriors (higher damage), but alternate to spawn farmers too
        should_spawn = False
        spawn_type = None

        if wheat >= 12 and len(remaining_farmers) >= 4:
            # Safe spawn: keep at least 2 farming
            should_spawn = True
        elif wheat >= 18 and len(remaining_farmers) >= 2:
            # Aggressive spawn: have enough wheat buffer even if no farming this step
            should_spawn = True

        if should_spawn:
            # Alternate between spawning warriors and farmers
            # Warriors are more important for damage, so spawn warriors more often
            if self._spawn_counter % 3 < 2:
                # Spawn warrior (every 3 steps, 2 out of 3 times)
                if wheat >= 12:
                    spawn_type = "spawn warrior"
                    self._spawn_counter += 1
                elif wheat >= 10:
                    spawn_type = "spawn farmer"
                    self._spawn_counter += 1
            else:
                # Spawn farmer (every 3 steps, 1 out of 3 times)
                if wheat >= 10:
                    spawn_type = "spawn farmer"
                    self._spawn_counter += 1
                elif wheat >= 12:
                    spawn_type = "spawn warrior"
                    self._spawn_counter += 1

            if spawn_type and len(remaining_farmers) >= 2:
                for f in remaining_farmers[:2]:
                    environment.assign_group(f, spawn_type)
                remaining_farmers = remaining_farmers[2:]

        # All remaining farmers produce wheat
        for f in remaining_farmers:
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the cave, warriors should always attack the dragon
        # Any non-warrior units should be sent back to village
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                # Farmers in cave (shouldn't normally happen) go back to village
                environment.assign_group(c, "village")
```

**Key design decisions:**
- **Warriors go to cave on step 1**, ensuring they can attack by step 2 (well within the 15-step deadline).
- **Farmers stay in village** and alternate between farming and spawning. Spawning requires wheat ≥12 (warrior) or ≥10 (farmer) plus 2 villagers in the spawn group.
- **Spawning alternates 2:1 warrior:farmer** using a counter, ensuring both types are produced (satisfying "at least a few of each").
- **All warriors in cave always attack**, maximizing damage output against the 50 HP dragon (each warrior deals 3 damage per step).
- **Conservative resource management**: we only spawn when we have sufficient wheat buffer, preventing resource starvation.