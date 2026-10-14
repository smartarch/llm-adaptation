

# Adaptation Strategy for Dragon Hunt

## Strategy Description

The goal is to kill a 50 HP Dragon within 30 steps while maintaining village production and spawning reinforcements. Here's the phased strategy:

**Core Principles:**
- **Village phase:** All warriors are sent to the cave immediately. Farmers stay in village, primarily farming for wheat. Excess farmers are used for spawning (warriors first for damage output, then farmers for sustainability).
- **Cave phase:** All warriors immediately attack the dragon upon arrival. Warriors with critical HP (≤1) are sent back to village to survive, then re-deployed.
- **Early game priority:** Ensure at least one warrior reaches the cave by step 1-2 to satisfy the "attack within 15 steps" requirement.

**Spawning logic:** Once we have ≥5 farmers, we keep 2-3 farming and dedicate 2 to "spawn warrior" (cost 12 wheat) for more damage dealers. We use another 2 for "spawn farmer" (cost 10 wheat) if we still have excess.

**Cave logic:** Warriors attack aggressively. Only retreat if HP ≤ 1 (about to die from the dragon's 40% AoE hit).

## Implementation

```py
import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartDragonHuntAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step):
        """
        Village assignment:
        - All warriors -> "cave" (go to cave to attack)
        - Farmers -> mostly "farm", some to "spawn warrior" / "spawn farmer"
        """
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # Try to get current wheat from environment
        wheat = getattr(environment, 'wheat', 0)

        # --- Assign all warriors to cave (Requirements 3, 6, 7, 2) ---
        for w in warriors:
            environment.assign_group(w, "cave")

        # --- Assign farmers (Requirement 4: stay in village) ---
        if len(farmers) == 0:
            return

        if len(farmers) <= 3:
            # Small village: all farmers just farm
            for f in farmers:
                environment.assign_group(f, "farm")
            return

        # Larger village: keep minimum farmers farming, use rest for spawning
        # Need at least 2 farmers always farming for food production
        num_farming = max(2, len(farmers) - 4)  # keep 2-3 farming
        farming_list = farmers[:num_farming]
        available_for_spawn = farmers[num_farming:]

        # Assign farming farmers
        for f in farming_list:
            environment.assign_group(f, "farm")

        # Priority: spawn warriors first (more damage output)
        if len(available_for_spawn) >= 2 and wheat >= 12:
            for f in available_for_spawn[:2]:
                environment.assign_group(f, "spawn warrior")
            available_for_spawn = available_for_spawn[2:]

        # Then spawn farmers if we still have excess
        if len(available_for_spawn) >= 2 and wheat >= 10:
            for f in available_for_spawn[:2]:
                environment.assign_group(f, "spawn farmer")
            available_for_spawn = available_for_spawn[2:]

        # Any remaining farmers go to farm
        for f in available_for_spawn:
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        """
        Cave assignment:
        - All warriors -> "attack" (Requirement 6: attack after arriving)
        - Critical HP warriors -> "village" (survive to fight another day)
        - Any farmers in cave -> "village" (Requirement 4: return them)
        """
        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        # Send all farmers back to village immediately
        for f in farmers:
            environment.assign_group(f, "village")

        # Assign warriors: attack if healthy, retreat if critical
        for w in warriors:
            if w.hp <= 1:
                # Critical: retreat to survive, will be sent back next step
                environment.assign_group(w, "village")
            else:
                # Attack the dragon (Requirement 6, 7)
                environment.assign_group(w, "attack")
```

This strategy ensures:
- **Requirement 1:** Sustained warrior attacks (3 dmg each) will kill the 50 HP dragon in ~4-5 rounds with 3-4 warriors attacking simultaneously.
- **Requirement 2:** Warriors are sent to cave on step 0, so attack happens by step 1-2.
- **Requirements 3 & 4:** Warriors→cave, Farmers→village.
- **Requirements 5 & 6:** Spawning logic creates new warriors/farmers when wheat accumulates.
- **Requirement 7:** All (or nearly all) warriors are in cave attacking; only critical-HP warriors briefly retreat.