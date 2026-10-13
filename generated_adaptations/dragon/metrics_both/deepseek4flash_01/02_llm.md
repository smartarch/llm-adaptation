The strategy prioritizes a stable economy while ensuring an early attack:

- **Village:** All warriors are immediately sent to the Cave. Farmers are kept in the Village and assigned either to farm or to spawn new villagers. We first spawn an emergency warrior if no warrior has ever been seen, then guarantee at least two new farmers and two new warriors, then grow the farmer economy to about eight farmers, and finally keep spawning warriors whenever wheat allows. Each spawn uses exactly two farmers in the spawn group so that one new villager is produced per spawn action.
- **Cave:** All warriors are assigned to attack the Dragon. Any farmers that end up in the Cave are sent back to the Village.
- **State tracking:** The adaptation remembers how many farmers/warriors it has already spawned and whether any warrior has been observed, so it can react correctly even when initial villagers differ.

This satisfies the requirements: warriors always move to the Cave and attack, farmers stay in the Village, at least a few new farmers and warriors are spawned, and the Dragon is attacked early (within the first 15 steps).

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.spawned_farmers = 0
        self.spawned_warriors = 0
        self.has_seen_warrior = False

    def assign_in_village(self, components, environment, group_ids, step: int):
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        if warriors:
            self.has_seen_warrior = True

        # All warriors go to the Cave immediately.
        for w in warriors:
            environment.assign_group(w, "cave")

        wheat = getattr(environment.farm, "wheat", 0)
        num_farmers = len(farmers)

        spawn_action = None  # None, "spawn farmer", or "spawn warrior"

        # 1. If no warrior has ever been seen, spawn one as soon as possible.
        if not self.has_seen_warrior and num_farmers >= 2 and wheat >= 12:
            spawn_action = "spawn warrior"
            self.spawned_warriors += 1
        # 2. Ensure at least two new farmers are spawned.
        elif self.spawned_farmers < 2 and num_farmers >= 2 and wheat >= 10:
            spawn_action = "spawn farmer"
            self.spawned_farmers += 1
        # 3. Ensure at least two new warriors are spawned.
        elif self.spawned_warriors < 2 and num_farmers >= 2 and wheat >= 12:
            spawn_action = "spawn warrior"
            self.spawned_warriors += 1
        # 4. Grow the farmer economy if it is still small.
        elif (self.spawned_farmers < 6 and num_farmers < 8
              and num_farmers >= 2 and wheat >= 10):
            spawn_action = "spawn farmer"
            self.spawned_farmers += 1
        # 5. Otherwise, keep spawning warriors as long as the economy allows.
        elif num_farmers >= 2 and wheat >= 12:
            spawn_action = "spawn warrior"
            self.spawned_warriors += 1

        if spawn_action == "spawn farmer":
            for i, f in enumerate(farmers):
                if i < 2:
                    environment.assign_group(f, "spawn farmer")
                else:
                    environment.assign_group(f, "farm")
        elif spawn_action == "spawn warrior":
            for i, f in enumerate(farmers):
                if i < 2:
                    environment.assign_group(f, "spawn warrior")
                else:
                    environment.assign_group(f, "farm")
        else:
            for f in farmers:
                environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        if any(getattr(c, "role", None) == "Warrior" for c in components):
            self.has_seen_warrior = True

        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                # All warriors attack the Dragon.
                environment.assign_group(c, "attack")
            else:
                # Farmers should stay in the Village.
                environment.assign_group(c, "village")
```