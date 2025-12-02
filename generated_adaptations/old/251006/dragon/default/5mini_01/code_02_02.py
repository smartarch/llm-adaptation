from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Improved SmartAdaptation implementing the strategy described above.

    Key changes vs previous version:
    - If exactly 2 farmers exist and wheat >= 12, spawn a warrior immediately by assigning both farmers
      to "spawn warrior". This ensures at least one warrior is produced early.
    - With >=3 farmers, keep one farming (income) and use remaining farmers in pairs to spawn warriors
      first (12 wheat per pair) then farmers (10 wheat per pair).
    - Warriors in village are sent to cave. Warriors in cave attack. Farmers in cave are sent back to village.
    """

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Group names: "farm", "cave", "spawn farmer", "spawn warrior"
        farmers = [c for c in components if getattr(c, "role", "").lower() == "farmer"]
        warriors = [c for c in components if getattr(c, "role", "").lower() == "warrior"]

        # Send all warriors in the village to the cave
        for w in warriors:
            environment.assign_group(w, "cave")

        total_farmers = len(farmers)
        if total_farmers == 0:
            return

        # Read available wheat (read-only). Use it to decide spawning this step.
        try:
            sim_wheat = int(environment.farm.wheat)
        except Exception:
            # fallback if attribute not present or convertible, treat as 0
            sim_wheat = 0

        # If exactly two farmers: either both farm (to accumulate wheat) or both spawn a warrior if wheat allows.
        if total_farmers == 2:
            if sim_wheat >= 12:
                # spawn a warrior using these two farmers
                for f in farmers:
                    environment.assign_group(f, "spawn warrior")
                return
            else:
                # keep both farming to reach spawn threshold sooner
                for f in farmers:
                    environment.assign_group(f, "farm")
                return

        # If only one farmer, keep farming
        if total_farmers == 1:
            environment.assign_group(farmers[0], "farm")
            return

        # For 3 or more farmers:
        # Reserve one farmer to farm each step to maintain wheat income
        reserved = farmers[0]
        remaining = farmers[1:]  # list of farmer objects available for spawning or farming
        environment.assign_group(reserved, "farm")

        # Now use pairs from remaining to spawn warriors first, then farmers
        remaining_count = len(remaining)
        # Number of pairs available
        pairs_available = remaining_count // 2

        # Spawn as many warriors as possible given wheat and pairs
        spawn_warrior_pairs = min(pairs_available, sim_wheat // 12)
        # Assign pairs for warrior spawns
        idx = 0
        for _ in range(spawn_warrior_pairs):
            if idx + 1 < len(remaining):
                environment.assign_group(remaining[idx], "spawn warrior")
                environment.assign_group(remaining[idx + 1], "spawn warrior")
                idx += 2
                sim_wheat -= 12
            else:
                break

        # Recompute pairs available from remaining unassigned farmers
        pairs_left = (len(remaining) - idx) // 2

        # Spawn farmers with remaining pairs if wheat allows
        spawn_farmer_pairs = min(pairs_left, sim_wheat // 10)
        for _ in range(spawn_farmer_pairs):
            if idx + 1 < len(remaining):
                environment.assign_group(remaining[idx], "spawn farmer")
                environment.assign_group(remaining[idx + 1], "spawn farmer")
                idx += 2
                sim_wheat -= 10
            else:
                break

        # Any leftover unassigned farmers go to farm
        while idx < len(remaining):
            environment.assign_group(remaining[idx], "farm")
            idx += 1

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # Group names: "attack", "cave", "village"
        for c in components:
            role = getattr(c, "role", "").lower()
            if role == "warrior":
                environment.assign_group(c, "attack")
            else:
                # All farmers in cave are sent back to village to protect the economy
                environment.assign_group(c, "village")