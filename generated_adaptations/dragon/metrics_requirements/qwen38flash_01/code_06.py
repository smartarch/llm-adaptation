import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step):
        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        # Rule: every warrior in village must head to the cave.
        for w in warriors:
            environment.assign_group(w, "cave")

        if not farmers:
            return

        # Read available wheat defensively.
        wheat = 0
        try:
            wheat = int(getattr(environment, "wheat", 0) or 0)
        except Exception:
            wheat = 0

        # Spawn priority: warriors (we need damage output to kill the dragon).
        # A spawn group needs exactly 2 farmers in it and enough wheat.
        spawn_used = 0
        if len(farmers) >= 3 and wheat >= 12:
            # Leave at least 1 farmer farming; we have 3+ so 2 can spawn.
            environment.assign_group(farmers[0], "spawn warrior")
            environment.assign_group(farmers[1], "spawn warrior")
            spawn_used = 2

        # Remaining farmers go to farm (they generate the wheat for next spawns).
        for f in farmers[spawn_used:]:
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        # Every warrior in the cave must be attacking the dragon.
        # Any non-warrior that ended up here goes back to the village.
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")