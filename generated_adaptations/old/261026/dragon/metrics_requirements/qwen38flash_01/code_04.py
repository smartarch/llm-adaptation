import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartDragonHuntAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step):
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # --- All warriors MUST go to cave (requirements 3, 6, 7) ---
        for w in warriors:
            environment.assign_group(w, "cave")

        # --- Farmer allocation ---
        if not farmers:
            return

        # Try to read wheat available
        try:
            wheat = getattr(environment, 'wheat', 0)
        except Exception:
            wheat = 0

        # We need at least 2 farmers in a spawn group, and wheat to afford it
        assigned_spawn = False

        # PRIORITY: spawn warriors (3 dmg vs dragon)
        if len(farmers) >= 2 and wheat >= 12:
            # Use 2 farmers to spawn warrior
            environment.assign_group(farmers[0], "spawn warrior")
            environment.assign_group(farmers[1], "spawn warrior")
            assigned_spawn = True
            farmers_left = farmers[2:]
        # SECONDARY: spawn farmers to expand economy (only if we have extra farmers)
        elif len(farmers) >= 3 and wheat >= 10:
            environment.assign_group(farmers[0], "spawn farmer")
            environment.assign_group(farmers[1], "spawn farmer")
            assigned_spawn = True
            farmers_left = farmers[2:]
        else:
            farmers_left = farmers

        # All remaining farmers farm (requirement 4: stay in village)
        for f in farmers_left:
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        # ALL warriors in cave MUST attack (requirements 6, 7)
        # No retreating - they fight to the death
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                # Any farmer who ended up in cave gets sent back
                environment.assign_group(c, "village")