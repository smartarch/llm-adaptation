

## Adaptation Strategy

**Overview:**
- **Warriors in Village:** Eat if `steps_since_meal >= 4` (otherwise they'd arrive in cave already too weak to attack). Otherwise, go to cave immediately to attack the Dragon.
- **Warriors in Cave:** Attack every step unless `steps_since_meal >= 5` (about to starve, must return to village to eat, accepting 1 HP loss). Farmers accidentally in cave are sent back.
- **Farmers in Village:** Eat if hungry (`ssm >= 4`). Otherwise, use them to spawn warriors (priority, up to 4 total) and farmers (up to 2 total), keeping the rest farming.
- **Spawning:** Aggressively spawn warriors for DPS since the Dragon needs sustained 3-damage attacks to die within 30 steps. Stagger warrior meal cycles to ensure no more than 2 consecutive steps without attack.

**Key design choices:**
- Warrior threshold for eating in village: ssm ≥ 4 ensures they arrive at cave with ssm ≤ 1, giving at least 3-4 attacks before returning.
- Warrior threshold for leaving cave: ssm ≥ 5 (they attack at ssm=4 then return, costing 1 HP per trip but maximizing DPS).
- Track spawning count to hit the "at least 2 of each" requirement and add extra warriors for damage.
- Maintain at least 1 farmer farming to sustain wheat production.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation
import abc


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._spawned_warriors = 0
        self._spawned_farmers = 0
        self._warriors_in_cave_estimate = 0

    def assign_in_village(self, components, environment, group_ids, step):
        wheat = environment.farm.wheat

        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        # --- Warriors in Village ---
        # Eat if too hungry to be useful in cave (ssm >= 4 means they'd arrive
        # at ssm=5 and might starve during attack). Otherwise send to cave.
        for w in warriors:
            if w.steps_since_meal >= 4:
                environment.assign_group(w, "eat")
            else:
                environment.assign_group(w, "cave")

        # --- Farmers in Village ---
        # Categorize by hunger
        hungry_farmers = [f for f in farmers if f.steps_since_meal >= 4]
        full_farmers = [f for f in farmers if f.steps_since_meal < 4]

        # Hungry farmers must eat
        for f in hungry_farmers:
            environment.assign_group(f, "eat")

        # From available (fed) farmers, allocate to: spawn warrior > spawn farmer > farm
        # Must keep at least 1 farmer farming if possible
        idx = 0
        n = len(full_farmers)

        # Keep at least 1 farmer farming for wheat production
        min_farming = 1

        # Spawn warriors aggressively (target up to 4 total spawned warriors)
        while (self._spawned_warriors < 4) and (n - idx >= 2 + min_farming) and wheat >= 12:
            environment.assign_group(full_farmers[idx], "spawn warrior")
            environment.assign_group(full_farmers[idx + 1], "spawn warrior")
            self._spawned_warriors += 1
            wheat -= 12
            idx += 2

        # Spawn farmers (target 2 total spawned farmers)
        while (self._spawned_farmers < 2) and (n - idx >= 2 + min_farming) and wheat >= 10:
            environment.assign_group(full_farmers[idx], "spawn farmer")
            environment.assign_group(full_farmers[idx + 1], "spawn farmer")
            self._spawned_farmers += 1
            wheat -= 10
            idx += 2

        # Remaining farmers farm
        for f in full_farmers[idx:]:
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        # Farmers should never be in the cave; send them back to village
        for f in farmers:
            environment.assign_group(f, "village")

        # Warriors: attack the Dragon unless about to starve
        # At ssm >= 5, they must return to eat. Movement to village costs 1 HP
        # (ssm hits 6 during transit) but they eat the next step and are fine.
        # At ssm <= 4, they can safely attack.
        for w in warriors:
            if w.steps_since_meal >= 5:
                environment.assign_group(w, "village")
            else:
                environment.assign_group(w, "attack")
```