from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Divide villagers in the Village into:
        - farm: stay and farm
        - cave: go to the Cave (will be moved to attack in cave phase)
        - spawn farmer: for every two villagers assigned here and 10 wheat, spawn a Farmer
        - spawn warrior: for every two villagers assigned here and 12 wheat, spawn a Warrior
        Strategy:
        - Move all Warriors to the Cave (to attack later).
        - For Farmers, allocate some to spawn farmers and spawn warriors based on available wheat.
        - Remaining farmers go to farming.
        - This keeps a balance between growing wheat (to enable spawns) and spawning new villagers.
        """
        # Separate current villagers by role
        farmers = [c for c in components if getattr(c, "role", "") == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", "") == "Warrior"]

        # If there are no farmers, we cannot spawn. We'll just move warriors to cave, and farmers (if any) to farm (none in this case).
        wheat = getattr(environment.farm, "wheat", 0)

        # Compute how many spawns we can perform this step given the wheat and available farmers
        spawns_farm = 0
        spawns_war = 0

        if len(farmers) >= 2:
            spawns_farm = min(len(farmers) // 2, wheat // 10)
            remaining_farmers_after_farm = len(farmers) - (spawns_farm * 2)
            # Re-evaluate wheat after reserving for farmer spawns
            wheat_after_farm = max(0, wheat - (spawns_farm * 10))
            spawns_war = 0
            if remaining_farmers_after_farm >= 2:
                spawns_war = min(remaining_farmers_after_farm // 2, wheat_after_farm // 12)

        # Assign groups for farmers
        # We will assign in order: first 2*spawns_farm to "spawn farmer",
        # next 2*spawns_war to "spawn warrior",
        # the rest to "farm"
        for idx, f in enumerate(farmers):
            if idx < spawns_farm * 2:
                environment.assign_group(f, "spawn farmer")
            elif idx < (spawns_farm * 2) + (spawns_war * 2):
                environment.assign_group(f, "spawn warrior")
            else:
                environment.assign_group(f, "farm")

        # Assign all Warriors to cave (to move to Cave)
        for w in warriors:
            environment.assign_group(w, "cave")

        # Note: If there are any villagers not covered (unexpected cases), default to staying in farm
        # (This ensures every component is assigned to one of the valid groups.)
        # (All villagers should have been assigned by now.)
        # Safety check (optional): ensure every component is assigned at least to something
        # (not strictly necessary; engine will ignore duplicates.)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Divide villagers in the Cave into:
        - attack: Attack the Dragon
        - cave: Stay in the Cave
        - village: Go to the Village
        Strategy:
        - All Warriors should attack the Dragon, so assign all Warriors to "attack".
        - All Farmers should return to the Village, so assign them to "village".
        - This keeps farmers in the Village and ensures warriors are ready to attack.
        """
        for c in components:
            role = getattr(c, "role", "")
            if role == "Warrior":
                environment.assign_group(c, "attack")
            elif role == "Farmer":
                environment.assign_group(c, "village")
            else:
                # Fallback: keep in cave if unknown role
                environment.assign_group(c, "cave")