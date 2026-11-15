

## Analysis of v2 Failure

The v2 strategy dropped to 67% win rate because:
1. **Sending farmers to cave** removed critical wheat production and spawned warriors died more
2. **Allowing warriors to reach scm=5-6 before leaving** caused starvation and HP loss, leading to village deaths
3. **Complex endgame thresholds** (HP ≤ 20, 25) triggered prematurely, wasting resources

## v3 Strategy: Optimized v1

I'm going back to the reliable v1 approach (100% win rate) but optimizing for speed:
- **Aggressive continuous warrior spawning** whenever wheat ≥ 12 (not gated by step ranges)
- **Tight warrior rotation**: eat at scm≥4, enter cave at scm≤2, leave cave at scm≥4 (3 attacks per cycle, fully safe)
- **Simple endgame**: Dragon HP ≤ 9 triggers all-in (few steps remain, starvation risk is acceptable)
- **Never send farmers to cave** — they're too weak and removing them from farming slows warrior pipeline
- **Maintain 2 farmers minimum** for wheat production to sustain warrior pipeline

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step):
        wheat = environment.farm.wheat
        dragon_hp = environment.dragon.hp

        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        # --- Warriors in Village ---
        for w in warriors:
            if w.steps_since_meal >= 4:
                environment.assign_group(w, "eat")
            else:
                # scm 0-3: safe to go to cave (arrive scm 1-4, can attack 1-3 times)
                environment.assign_group(w, "cave")

        # --- Farmers in Village ---
        hungry_farmers = [f for f in farmers if f.steps_since_meal >= 4]
        available_farmers = [f for f in farmers if f.steps_since_meal < 4]

        for f in hungry_farmers:
            environment.assign_group(f, "eat")

        # --- Spawning: aggressively spawn warriors ---
        # Always try to spawn warriors if we have resources, keep at least 2 farmers farming
        spawn_available = available_farmers  # farmers not eating

        if len(spawn_available) >= 2:
            if wheat >= 12:
                # Spawn warrior - this is the priority for killing the dragon
                environment.assign_group(spawn_available[0], "spawn warrior")
                environment.assign_group(spawn_available[1], "spawn warrior")
                spawn_available = spawn_available[2:]
            elif wheat >= 10 and step <= 4:
                # Very early: spawn a farmer to boost wheat economy
                environment.assign_group(spawn_available[0], "spawn farmer")
                environment.assign_group(spawn_available[1], "spawn farmer")
                spawn_available = spawn_available[2:]

        # Remaining farmers farm
        for f in spawn_available:
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        dragon_hp = environment.dragon.hp

        for c in components:
            if c.role == "Warrior":
                if dragon_hp <= 9:
                    # Endgame: attack regardless of hunger - game will end in <3 steps
                    environment.assign_group(c, "attack")
                elif c.steps_since_meal >= 4:
                    # Leave now: arrive village at scm=5, eat safely next step
                    environment.assign_group(c, "village")
                else:
                    # scm 0-3: attack
                    environment.assign_group(c, "attack")
            elif c.role == "Farmer":
                # Farmers in cave should leave immediately (they're not useful here)
                # Unless it's absolute endgame where we need every hit
                if dragon_hp <= 3 and c.steps_since_meal < 5:
                    environment.assign_group(c, "attack")
                else:
                    environment.assign_group(c, "village")
```