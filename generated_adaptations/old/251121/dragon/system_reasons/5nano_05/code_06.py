from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate existing farmers and warriors in the village
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # Move all existing warriors to the cave to start marching towards the Dragon
        for w in warriors:
            environment.assign_group(w, "cave")

        # Early steps: focus on farming to accumulate wheat
        if step <= 3 or len(farmers) == 0:
            for f in farmers:
                environment.assign_group(f, "farm")
            return

        # Wheat available for spawning
        wheat = getattr(environment.farm, "wheat", 0)

        # Reserve a fraction of farmers for ongoing farming (to sustain wheat production)
        reserve = max(1, int(len(farmers) * 0.25))

        # Potential spawner farmers are those not reserved for ongoing farming
        potential_spawners = farmers

        # Farmer-spawns: need 2 farmers + 10 wheat per spawn
        f_spawns = min((len(potential_spawners) - reserve) // 2 if len(potential_spawners) > reserve else 0,
                       wheat // 10)

        wheat_after_f_farm = wheat - f_spawns * 10

        # Warrior-spawns: need 2 farmers + 12 wheat per spawn
        remaining_for_w_spawns = max(0, len(potential_spawners) - reserve - 2 * f_spawns)
        w_spawns = min(remaining_for_w_spawns // 2, wheat_after_f_farm // 12)

        # Assign each farmer to exactly one group in a single pass
        # First 2*f_spawns farmers -> "spawn farmer"
        # Next 2*w_spawns farmers -> "spawn warrior"
        # Remaining farmers (including those reserved for farming) -> "farm"
        total_farmers = len(farmers)
        for idx, f in enumerate(farmers):
            if idx < 2 * f_spawns:
                environment.assign_group(f, "spawn farmer")
            elif idx < 2 * f_spawns + 2 * w_spawns:
                environment.assign_group(f, "spawn warrior")
            else:
                environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the cave, attack with warriors; farmers go back to village
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")