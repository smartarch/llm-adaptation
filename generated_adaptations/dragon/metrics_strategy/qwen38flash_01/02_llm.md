

## Strategy Description

My adaptation strategy follows a "Warrior Rotation with Aggressive Early Spawning" approach:

**Core Principles:**
1. **Warriors are the DPS engine** — they go to the Cave ASAP, attack, and rotate back for meals in a tight cycle
2. **Farmers are the economy engine** — they farm wheat and spawn new warriors (priority) and farmers
3. **Meal timing** — Warriors leave the Cave at `steps_since_meal >= 4` (arrive at Village at 5, eat safely under the 6-step starvation threshold). They only go back to the Cave if `steps_since_meal <= 2` (ensuring at least 1 attack before needing to return)
4. **Dragon pressure** — With multiple warriors staggered, the Dragon is attacked nearly every step (max 2 gaps), preventing regeneration
5. **Early aggression** — First warrior attacks by step 2; warriors spawned as fast as wheat allows; Dragon must be hit by step 15 (easily achieved)
6. **Spawn priority** — Warriors first (3 dmg > 1 dmg), then farmers for wheat economy; at least 2 of each
7. **Low-HP finish** — When Dragon HP ≤ 12, even hungry warriors attack (the game will end before they starve)

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step):
        wheat = environment.farm.wheat

        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        # --- Warriors in Village: eat if hungry, otherwise return to Cave ---
        for w in warriors:
            if w.steps_since_meal >= 4:
                environment.assign_group(w, "eat")
            elif w.steps_since_meal <= 2:
                # Safe to send: will arrive at Cave with steps_since_meal <= 3,
                # guaranteeing at least one attack before needing to return.
                environment.assign_group(w, "cave")
            else:
                # steps_since_meal == 3: eat to be safe, avoid arriving at 4+
                environment.assign_group(w, "eat")

        # --- Farmers in Village: handle eating, spawning, farming ---
        hungry_farmers = []
        available_farmers = []
        for f in farmers:
            if f.steps_since_meal >= 4:
                environment.assign_group(f, "eat")
                hungry_farmers.append(f)
            else:
                available_farmers.append(f)

        # Count total warriors (rough proxy: warriors present + those in cave)
        # For spawning logic, use step-based heuristic since we can't see Cave contents
        # directly from here.

        # Spawning logic: use available (non-hungry) farmers in pairs
        spawn_pairs_needed = 0
        spawn_type = None

        if step <= 8 and wheat >= 12 and len(available_farmers) >= 2:
            # Priority: spawn Warriors early for damage
            spawn_pairs_needed = 1
            spawn_type = "spawn warrior"
        elif step <= 14 and wheat >= 12 and len(available_farmers) >= 2:
            spawn_pairs_needed = 1
            spawn_type = "spawn warrior"
        elif step <= 18 and wheat >= 10 and len(available_farmers) >= 2:
            # Spawn a Farmer to boost wheat economy
            spawn_pairs_needed = 1
            spawn_type = "spawn farmer"
        elif step > 18 and wheat >= 12 and len(available_farmers) >= 4:
            # Late game: one more warrior if we can afford it
            spawn_pairs_needed = 1
            spawn_type = "spawn warrior"

        if spawn_pairs_needed > 0 and spawn_type:
            environment.assign_group(available_farmers[0], spawn_type)
            environment.assign_group(available_farmers[1], spawn_type)
            remaining_farmers = available_farmers[2:]
        else:
            remaining_farmers = available_farmers

        # All remaining farmers farm
        for f in remaining_farmers:
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        dragon_hp = environment.dragon.hp

        for c in components:
            if c.role == "Warrior":
                # If Dragon is nearly dead, push through hunger
                if dragon_hp <= 12:
                    environment.assign_group(c, "attack")
                elif c.steps_since_meal >= 4:
                    # Must leave to eat: arrive Village at scm=5, eat safely
                    environment.assign_group(c, "village")
                else:
                    environment.assign_group(c, "attack")
            elif c.role == "Farmer":
                # Farmers in cave (rare) should still help
                if c.steps_since_meal >= 4:
                    environment.assign_group(c, "village")
                elif dragon_hp <= 12:
                    environment.assign_group(c, "attack")
                else:
                    # Farmers only deal 1 dmg; better to farm in Village
                    # but if they're already here, they can still chip in
                    # unless they need to eat soon
                    environment.assign_group(c, "village")
```

**Key Design Decisions:**

- **Warrior rotation cycle** (~7 steps): Eat → Travel to Cave → Attack ×3 → Travel back → (Eat). This keeps warriors at ≤5 consecutive steps without food.
- **Cave exit at `scm ≥ 4`**: Guarantees arrival at Village at `scm = 5 < 6`, avoiding starvation.
- **Cave entry only at `scm ≤ 2`**: Ensures the warrior can attack at least once (arrives at `scm ≤ 3`, attacks, leaves at `scm = 4`).
- **Spawn warriors aggressively in steps 0–14** to build DPS before the Dragon gets a long regen streak.
- **Staggered warrior entry** (different spawn times naturally create stagger) ensures near-continuous Dragon pressure.
- **Finisher mode** (`dragon_hp ≤ 12`): All warriors attack regardless of hunger since the game ends before starvation becomes relevant.