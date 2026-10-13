The strategy is:

- In the **Village**:
  - All warriors are immediately assigned to `"cave"`.
  - Farmers default to `"farm"`, but some are temporarily assigned to spawn groups.
  - If no warrior has ever been seen, we prioritize spawning a warrior first to satisfy the early-attack requirement.
  - Otherwise, we keep spawn counts balanced toward at least a few farmers and a few warriors, then continue spawning only when there is surplus wheat.
- In the **Cave**:
  - All warriors are assigned to `"attack"`.
  - Any farmers in the cave are sent back with `"village"`.

Every component is explicitly assigned on every call, including when it remains in the same role.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.spawned_farmers = 0
        self.spawned_warriors = 0
        self.has_warrior = False
        self.target_farmers = 4
        self.target_warriors = 4

    def assign_in_village(self, components, environment, group_ids, step: int):
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        if warriors:
            self.has_warrior = True

        # All warriors go to the cave so they can attack the Dragon.
        for w in warriors:
            environment.assign_group(w, "cave")

        wheat = environment.farm.wheat
        n_farmers = len(farmers)

        spawn_type = None

        if n_farmers >= 2:
            if not self.has_warrior:
                # If no warrior has been seen yet, prioritize creating one.
                if wheat >= 12:
                    spawn_type = "spawn warrior"
                    self.spawned_warriors += 1
                    self.has_warrior = True
            else:
                need_warrior = self.spawned_warriors < self.target_warriors
                need_farmer = self.spawned_farmers < self.target_farmers

                if need_warrior and need_farmer:
                    # Keep farmer and warrior spawn counts balanced.
                    if self.spawned_warriors <= self.spawned_farmers:
                        if wheat >= 12:
                            spawn_type = "spawn warrior"
                            self.spawned_warriors += 1
                        elif wheat >= 10:
                            spawn_type = "spawn farmer"
                            self.spawned_farmers += 1
                    else:
                        if wheat >= 10:
                            spawn_type = "spawn farmer"
                            self.spawned_farmers += 1
                        elif wheat >= 12:
                            spawn_type = "spawn warrior"
                            self.spawned_warriors += 1
                elif need_warrior:
                    if wheat >= 12:
                        spawn_type = "spawn warrior"
                        self.spawned_warriors += 1
                elif need_farmer:
                    if wheat >= 10:
                        spawn_type = "spawn farmer"
                        self.spawned_farmers += 1
                else:
                    # After minimum targets are met, spawn only with surplus wheat.
                    if wheat >= 30 and n_farmers >= 4:
                        spawn_type = "both"
                        self.spawned_warriors += 1
                        self.spawned_farmers += 1
                    elif wheat >= 24 and step % 2 == 0:
                        spawn_type = "spawn warrior"
                        self.spawned_warriors += 1
                    elif wheat >= 20 and step % 2 == 1:
                        spawn_type = "spawn farmer"
                        self.spawned_farmers += 1

        # Assign every farmer exactly once.
        if spawn_type == "both":
            for f in farmers[:2]:
                environment.assign_group(f, "spawn warrior")
            for f in farmers[2:4]:
                environment.assign_group(f, "spawn farmer")
            for f in farmers[4:]:
                environment.assign_group(f, "farm")
        elif spawn_type is not None:
            for f in farmers[:2]:
                environment.assign_group(f, spawn_type)
            for f in farmers[2:]:
                environment.assign_group(f, "farm")
        else:
            for f in farmers:
                environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.role == "Warrior":
                self.has_warrior = True
                environment.assign_group(c, "attack")
            else:
                # Farmers belong in the village, not in the cave.
                environment.assign_group(c, "village")
```