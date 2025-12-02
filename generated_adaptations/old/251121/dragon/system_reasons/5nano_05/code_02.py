from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate farmers and warriors
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # Default: Farmers stay farming
        for f in farmers:
            environment.assign_group(f, "farm")

        # Move all warriors to cave (to travel to the Dragon)
        for w in warriors:
            environment.assign_group(w, "cave")

        # Spawning logic (spawn new villagers using two villagers + wheat)
        # Wheat available now
        wheat = getattr(environment.farm, "wheat", 0)

        # Number of spawn events for farmers: each needs 2 farmers + 10 wheat
        f_spawn_sets = min(len(farmers) // 2, wheat // 10)

        # After allocating farmer spawns, update wheat
        wheat_after_f_farm = wheat - f_spawn_sets * 10

        # Number of farmer-spawn events for warriors: each needs 2 farmers + 12 wheat
        remaining_farmers_for_warrior = len(farmers) - (f_spawn_sets * 2)
        w_spawn_sets = min(remaining_farmers_for_warrior // 2, wheat_after_f_farm // 12)

        # Allocate farmers to spawn groups
        # First: 2 * f_spawn_sets farmers to "spawn farmer"
        idx = 0
        for _ in range(2 * f_spawn_sets):
            if idx < len(farmers):
                environment.assign_group(farmers[idx], "spawn farmer")
                idx += 1

        # Next: 2 * w_spawn_sets farmers to "spawn warrior"
        for _ in range(2 * w_spawn_sets):
            if idx < len(farmers):
                environment.assign_group(farmers[idx], "spawn warrior")
                idx += 1

        # Remaining farmers go to farm
        while idx < len(farmers):
            environment.assign_group(farmers[idx], "farm")
            idx += 1

        # Warriors: ensure they are in cave (will be moved to attack in cave phase)
        # If there were no warriors (edge case), we leave as is.
        # Note: we already moved all warriors to "cave" above.

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the cave, we want all Warriors to attack and Farmers to go back to village
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                # Farmers should stay in Village
                environment.assign_group(c, "village")

        # Optional guard: ensure we attack within the first 15 steps
        # If there are no Warriors (rare), try to reassign a farming villager to attack if possible.
        if step <= 15:
            # Check if there is any Warrior already assigned to attack in this cave batch
            # We can't inspect current groups from here directly, so we rely on the above logic:
            # If there were no Warriors in this cave step, we do nothing extra.
            pass