## Adaptation strategy

The strategy separates the two roles and uses the spawn mechanics to build up both populations.

**In the Village (`assign_in_village`):**
- **Warriors** go straight to the Cave (`"cave"`) so they can start attacking as early as possible. Any warrior that is still in the Village gets the same order.
- **Farmers** are the economy. They stay on the farm (`"farm"`) by default. Two farmers at a time are diverted to a spawn group, and only when there is enough wheat for the spawn:
  - `"spawn warrior"` (needs 12 wheat) is tried first, up to two times, so that at least two new Warriors appear.
  - `"spawn farmer"` (needs 10 wheat) is then tried up to two times, so that at least two new Farmers appear.
  - A minimum of three farmers in the Village is required before any spawning, so that farming continues.
- Every component is assigned on every step, because an unassigned component does not keep its previous group.

**In the Cave (`assign_in_cave`):**
- All Warriors are assigned to `"attack"` on every step. This satisfies the requirement that they attack after arriving, and it ensures that the Dragon is hit within the first 15 steps.
- Any Farmer that ends up in the Cave is sent back to `"village"`, because Farmers should never fight.

**Assumptions and limits:**
- The strategy cannot read the spawn outcome directly, so it counts how many spawn attempts it has ordered and caps them at two per type. Those counters live on the instance and persist across steps.
- Warriors are not pulled out at low HP. This keeps damage output high and the Dragon's kill time short, at the risk of losing warriors to the Dragon's attacks.

```py
import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Warriors go to the Cave and attack the Dragon every step.
    Farmers stay on the farm and, when wheat allows, are temporarily
    assigned to spawn groups to create a few new Warriors and new Farmers.
    Any Farmer that ends up in the Cave is sent back to the Village.
    """

    MIN_FARMERS_FOR_SPAWNING = 3   # keep enough farmers working on the farm
    MAX_SPAWN_ATTEMPTS = 2         # attempts per spawn type (at least two of each)
    WARRIOR_SPAWN_COST = 12
    FARMER_SPAWN_COST = 10

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.warrior_spawn_attempts = 0
        self.farmer_spawn_attempts = 0

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat

        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        # Every warrior goes to the Cave to fight.
        for w in warriors:
            environment.assign_group(w, "cave")

        # Decide which farmers (if any) are used for spawning.
        spawn_warrior_group = []
        spawn_farmer_group = []
        remaining = list(farmers)

        if len(farmers) >= self.MIN_FARMERS_FOR_SPAWNING:
            # Prioritise warrior spawning (needs 2 villagers + 12 wheat).
            if (self.warrior_spawn_attempts < self.MAX_SPAWN_ATTEMPTS
                    and wheat >= self.WARRIOR_SPAWN_COST
                    and len(remaining) >= 2):
                spawn_warrior_group = remaining[:2]
                remaining = remaining[2:]
                self.warrior_spawn_attempts += 1

            # Then farmer spawning (needs 2 villagers + 10 wheat).
            if (self.farmer_spawn_attempts < self.MAX_SPAWN_ATTEMPTS
                    and wheat - (self.WARRIOR_SPAWN_COST if spawn_warrior_group else 0) >= self.FARMER_SPAWN_COST
                    and len(remaining) >= 2 + 1):  # keep at least one farmer farming
                spawn_farmer_group = remaining[:2]
                remaining = remaining[2:]
                self.farmer_spawn_attempts += 1

        # Assign spawn groups.
        for f in spawn_warrior_group:
            environment.assign_group(f, "spawn warrior")
        for f in spawn_farmer_group:
            environment.assign_group(f, "spawn farmer")

        # All other farmers keep farming.
        for f in remaining:
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                # Farmers do not fight; send them back to the Village.
                environment.assign_group(c, "village")
```