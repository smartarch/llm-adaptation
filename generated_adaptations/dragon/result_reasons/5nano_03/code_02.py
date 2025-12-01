from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Classify villagers currently in the village
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Strategy: all warriors go to the cave
        for w in warriors:
            environment.assign_group(w, "cave")

        # Spawn logic for farmers (in the village)
        # Get current wheat in the farm
        wheat = getattr(environment.farm, "wheat", 0)

        # Remaining unassigned farmers (start with all farmers)
        unassigned_farmers = list(farmers)

        # Attempt to spawn 1 Farmer: needs 2 farmers in this group and >= 10 wheat
        if len(unassigned_farmers) >= 2 and wheat >= 10:
            spawn_farmers = unassigned_farmers[:2]
            for f in spawn_farmers:
                environment.assign_group(f, "spawn farmer")
            unassigned_farmers = unassigned_farmers[2:]

        # Update wheat after potential spawn (the environment may account for this)
        # Attempt to spawn 1 Warrior: needs 2 more villagers in this group and >= 12 wheat
        if len(unassigned_farmers) >= 2 and wheat >= 12:
            spawn_warriors = unassigned_farmers[:2]
            for f in spawn_warriors:
                environment.assign_group(f, "spawn warrior")
            unassigned_farmers = unassigned_farmers[2:]

        # Remaining farmers stay in the village to farm
        for f in unassigned_farmers:
            environment.assign_group(f, "farm")

        # Note:
        # - All warriors are directed to the cave (attack ready).
        # - Farmers are kept in the village, with a small chance to spawn new villagers if resources allow.

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the cave: all Warriors should attack the Dragon; Farmers should go back to the Village
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                # Farmers should stay in the Village
                environment.assign_group(c, "village")