## Strategy: Warrior Rush with Wheat-Gated Farmer Spawning

**Cave phase:** Every Warrior in the Cave is assigned to `attack` so the Dragon takes damage from step one. Any Farmer that ends up in the Cave is sent back to the Village with `village`, since the rules keep Farmers out of combat. Warriors have 6 HP, so they can take a few Dragon counterattacks before dying.

**Village phase:**
- **Warriors** in the Village go to `cave` immediately.
- **Farmers** are split by need:
  - If wheat is at least 12 and at least 2 Farmers are present, two Farmers go to `spawn warrior`, until at least two Warriors have been spawned. Warriors are the main damage source, so this comes first.
  - Otherwise, if wheat is at least 10 and at least 2 Farmers are present, two Farmers go to `spawn farmer`, until at least two Farmers have been spawned.
  - Any remaining Farmers go to `farm`, so wheat keeps accumulating for spawns.
- **Spawn tracking:** The class estimates how many spawns have happened by watching for a wheat drop after a spawn group was assigned. This is an approximation, since the environment does not report spawns directly.

The Warrior-first ordering is intentional. The Dragon has 50 HP, and at 3 damage per Warrior hit, a handful of Warriors can finish it within the 30-step limit, while the Farmers keep the economy running for replacements.

```py
import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Warriors go to the cave and attack the Dragon from the first step.
    Farmers stay in the village, farming or being used to spawn
    new Farmers and Warriors (at least two of each).
    """

    FARMER_SPAWN_WHEAT = 10
    WARRIOR_SPAWN_WHEAT = 12
    MIN_SPAWNS_PER_ROLE = 2

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.spawned_farmers = 0
        self.spawned_warriors = 0
        # Bookkeeping for estimating spawns from wheat drops
        self.prev_wheat = None
        self.pending_spawn = None  # "farmer" or "warrior" if a spawn group was assigned last step

    def _update_spawn_estimate(self, environment):
        """Estimate whether a spawn happened last step by observing the wheat drop."""
        wheat = environment.farm.wheat
        if self.prev_wheat is not None and self.pending_spawn is not None:
            cost = (self.FARMER_SPAWN_WHEAT if self.pending_spawn == "farmer"
                    else self.WARRIOR_SPAWN_WHEAT)
            if wheat <= self.prev_wheat - cost:
                if self.pending_spawn == "farmer":
                    self.spawned_farmers += 1
                else:
                    self.spawned_warriors += 1
        self.prev_wheat = wheat
        self.pending_spawn = None
        return wheat

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = self._update_spawn_estimate(environment)

        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # All warriors head to the cave
        for w in warriors:
            environment.assign_group(w, "cave")

        # Decide on farmer usage
        available = list(farmers)
        spawn_warrior_group = []
        spawn_farmer_group = []

        need_warriors = self.spawned_warriors < self.MIN_SPAWNS_PER_ROLE
        need_farmers = self.spawned_farmers < self.MIN_SPAWNS_PER_ROLE

        if need_warriors and len(available) >= 2 and wheat >= self.WARRIOR_SPAWN_WHEAT:
            spawn_warrior_group = available[:2]
            available = available[2:]
            self.pending_spawn = "warrior"
        elif need_farmers and len(available) >= 2 and wheat >= self.FARMER_SPAWN_WHEAT:
            spawn_farmer_group = available[:2]
            available = available[2:]
            self.pending_spawn = "farmer"

        for f in spawn_warrior_group:
            environment.assign_group(f, "spawn warrior")
        for f in spawn_farmer_group:
            environment.assign_group(f, "spawn farmer")

        # Remaining farmers keep producing wheat
        for f in available:
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                # Farmers are not meant to fight; send them back to the village
                environment.assign_group(c, "village")
```