import abc

# The base class is provided by the environment:
# from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Divide Villagers in the Village into:
        - farm: Stay in the Village and farm
        - cave: Go to the Cave (will be attacked by Warriors already assigned to cave)
        - spawn farmer: For every two villagers assigned to this group and 10 wheat, spawn a new Farmer
        - spawn warrior: For every two villagers assigned to this group and 12 wheat, spawn a new Warrior
        """
        # Gather villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        wheat = int(getattr(environment.farm, "wheat", 0))

        # We'll use farmers to spawn both farmers and warriors
        # First, determine how many spawn-farmer pairs we can support with current wheat
        max_f_spawns = min(len(farmers) // 2, wheat // 10)

        # Assign 2 * max_f_spawns farmers to "spawn farmer"
        spawn_farmers = farmers[:2 * max_f_spawns]
        remaining_farmers_after_f = farmers[2 * max_f_spawns:]

        # Now determine how many spawn-warrior pairs we can support with remaining wheat
        # Each spawn-warrior requires 2 villagers (from farmers) and 12 wheat
        # Note: spawning uses wheat; the environment is expected to deduct wheat accordingly
        max_w_spawns = min(len(remaining_farmers_after_f) // 2, (wheat) // 12)

        spawn_warriors = remaining_farmers_after_f[:2 * max_w_spawns]
        remaining_farmers_after_w = remaining_farmers_after_f[2 * max_w_spawns:]

        # Remaining farmers go to farming
        farmers_to_farm = remaining_farmers_after_w

        # All Warriors go to the Cave (we attack later in assign_in_cave)
        for c in components:
            # Resetting assignments for clarity (enforces explicit reassignment)
            if getattr(c, "role", None) == "Warrior":
                self.environment.assign_group(c, "cave")
            else:
                # Farmers assignments
                if c in spawn_farmers:
                    self.environment.assign_group(c, "spawn farmer")
                elif c in spawn_warriors:
                    self.environment.assign_group(c, "spawn warrior")
                else:
                    self.environment.assign_group(c, "farm")

        # If there were any farmers not in a spawn group, ensure they are farming
        # (This covers edge cases where lists might be empty; the loop above already handles it)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Divide Villagers in the Cave into:
        - attack: Attack the Dragon
        - cave: Stay in the Cave
        - village: Go to the Village
        """
        # Clear current grouping by explicit assignment
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                # All Warriors in cave should attack
                self.environment.assign_group(c, "attack")
            else:
                # Farmers should go back to the Village
                self.environment.assign_group(c, "village")