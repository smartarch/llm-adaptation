from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Split villagers by role
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        assigned = set()

        #  spawn decisions based on available wheat and villagers
        wheat = getattr(environment.farm, "wheat", 0)

        # Try to spawn a Warrior if possible (needs two villagers and 12 wheat)
        if len(farmers) >= 2 and wheat >= 12:
            spawn_targets = farmers[:2]
            for f in spawn_targets:
                environment.assign_group(f, "spawn warrior")
                assigned.add(f)
        # If cannot spawn Warrior, try to spawn a Farmer (needs two villagers and 10 wheat)
        elif len(farmers) >= 2 and wheat >= 10:
            spawn_targets = farmers[:2]
            for f in spawn_targets:
                environment.assign_group(f, "spawn farmer")
                assigned.add(f)

        # After potential spawns, assign current cave wave (up to 2 Warriors) and rest to farm
        cave_slots = min(2, len(warriors))
        cave_assigned = 0

        # Assign Warriors to cave (current wave)
        for w in warriors:
            if w in assigned:
                continue
            if cave_assigned < cave_slots:
                environment.assign_group(w, "cave")
                cave_assigned += 1
                assigned.add(w)
            else:
                environment.assign_group(w, "farm")
                assigned.add(w)

        # Remaining Farmers go to farming unless they were assigned to spawn already
        for f in farmers:
            if f in assigned:
                continue
            # If we didn't spawn Warrior or Farmer this turn, stay farming
            environment.assign_group(f, "farm")
            assigned.add(f)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the cave, Warriors should attack; Farmers should go back to the village
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")