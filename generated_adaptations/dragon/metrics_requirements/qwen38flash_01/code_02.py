import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartDragonHuntAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step):
        """
        Village assignment:
        - All warriors -> "cave" (go to cave to attack)
        - Farmers -> mostly "farm", some to "spawn warrior" / "spawn farmer"
        """
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # Try to get current wheat from environment
        wheat = getattr(environment, 'wheat', 0)

        # --- Assign all warriors to cave (Requirements 3, 6, 7, 2) ---
        for w in warriors:
            environment.assign_group(w, "cave")

        # --- Assign farmers (Requirement 4: stay in village) ---
        if len(farmers) == 0:
            return

        if len(farmers) <= 3:
            # Small village: all farmers just farm
            for f in farmers:
                environment.assign_group(f, "farm")
            return

        # Larger village: keep minimum farmers farming, use rest for spawning
        # Need at least 2 farmers always farming for food production
        num_farming = max(2, len(farmers) - 4)  # keep 2-3 farming
        farming_list = farmers[:num_farming]
        available_for_spawn = farmers[num_farming:]

        # Assign farming farmers
        for f in farming_list:
            environment.assign_group(f, "farm")

        # Priority: spawn warriors first (more damage output)
        if len(available_for_spawn) >= 2 and wheat >= 12:
            for f in available_for_spawn[:2]:
                environment.assign_group(f, "spawn warrior")
            available_for_spawn = available_for_spawn[2:]

        # Then spawn farmers if we still have excess
        if len(available_for_spawn) >= 2 and wheat >= 10:
            for f in available_for_spawn[:2]:
                environment.assign_group(f, "spawn farmer")
            available_for_spawn = available_for_spawn[2:]

        # Any remaining farmers go to farm
        for f in available_for_spawn:
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        """
        Cave assignment:
        - All warriors -> "attack" (Requirement 6: attack after arriving)
        - Critical HP warriors -> "village" (survive to fight another day)
        - Any farmers in cave -> "village" (Requirement 4: return them)
        """
        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        # Send all farmers back to village immediately
        for f in farmers:
            environment.assign_group(f, "village")

        # Assign warriors: attack if healthy, retreat if critical
        for w in warriors:
            if w.hp <= 1:
                # Critical: retreat to survive, will be sent back next step
                environment.assign_group(w, "village")
            else:
                # Attack the dragon (Requirement 6, 7)
                environment.assign_group(w, "attack")