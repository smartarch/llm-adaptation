The adaptation strategy prioritizes a fast start and then snowballs into a warrior-heavy attack:

- **Cave assignment:** Every Warrior always attacks the Dragon. Any Farmer that ends up in the Cave is sent back to the Village to continue farming or spawning.
- **Village assignment:** Warriors are immediately sent to the Cave. Farmers are assigned dynamically:
  1. If no attack has happened yet and there are no Warriors in the Village, spawn as many Warriors as possible immediately (urgent attack phase).
  2. Otherwise, spawn up to 2 Farmers if we have not spawned 2 yet.
  3. Then spawn up to 2 Warriors if we have not spawned 2 yet.
  4. With any surplus wheat and farmers, spawn extra Warriors.
  5. Any remaining farmers work on the farm.

This ensures the Dragon is attacked early, at least two Farmers and two Warriors are spawned, and the economy keeps producing enough wheat to continuously reinforce the Cave with new Warriors.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.spawned_farmers = 0
        self.spawned_warriors = 0
        self.attacked = False

    def assign_in_village(self, components, environment, group_ids, step):
        wheat = environment.farm.wheat
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # All Warriors in the Village go to the Cave to attack.
        for w in warriors:
            environment.assign_group(w, "cave")

        n = len(farmers)
        if n == 0:
            return

        # Urgent: if we have not attacked yet and no Warriors are currently in
        # the Village, spawn as many Warriors as possible right now.
        urgent = (not self.attacked) and (len(warriors) == 0) and (step < 15)
        if urgent:
            max_warriors = min(n // 2, wheat // 12)
            if max_warriors > 0:
                for i in range(2 * max_warriors):
                    environment.assign_group(farmers[i], "spawn warrior")
                self.spawned_warriors += max_warriors
                for i in range(2 * max_warriors, n):
                    environment.assign_group(farmers[i], "farm")
            else:
                for f in farmers:
                    environment.assign_group(f, "farm")
            return

        need_farmers = max(0, 2 - self.spawned_farmers)
        need_warriors = max(0, 2 - self.spawned_warriors)

        idx = 0

        # Spawn the required number of Farmers.
        while need_farmers > 0 and idx + 2 <= n and wheat >= 10:
            environment.assign_group(farmers[idx], "spawn farmer")
            environment.assign_group(farmers[idx + 1], "spawn farmer")
            idx += 2
            wheat -= 10
            self.spawned_farmers += 1
            need_farmers -= 1

        # Spawn the required number of Warriors.
        while need_warriors > 0 and idx + 2 <= n and wheat >= 12:
            environment.assign_group(farmers[idx], "spawn warrior")
            environment.assign_group(farmers[idx + 1], "spawn warrior")
            idx += 2
            wheat -= 12
            self.spawned_warriors += 1
            need_warriors -= 1

        # Use any remaining wheat and farmers to spawn extra Warriors.
        remaining = n - idx
        max_extra = min(remaining // 2, wheat // 12)
        for _ in range(max_extra):
            if idx + 2 <= n:
                environment.assign_group(farmers[idx], "spawn warrior")
                environment.assign_group(farmers[idx + 1], "spawn warrior")
                idx += 2
                wheat -= 12
                self.spawned_warriors += 1

        # The rest work on the farm.
        while idx < n:
            environment.assign_group(farmers[idx], "farm")
            idx += 1

    def assign_in_cave(self, components, environment, group_ids, step):
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
                self.attacked = True
            else:
                # Farmers should stay in the Village.
                environment.assign_group(c, "village")
```