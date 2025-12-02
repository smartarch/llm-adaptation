from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Assign villagers in the Village into:
        - "farm": stay in Village and farm
        - "cave": go to the Cave (for Warriors to eventually attack)
        - "spawn farmer": for every 2 farmers assigned here and 10 wheat, a new Farmer spawns
        - "spawn warrior": for every 2 villagers assigned here and 12 wheat, a new Warrior spawns
        """
        # Separate Farmers and Warriors currently in the Village
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        current_wheat = getattr(getattr(environment, "farm", None), "wheat", 0)
        avail_farmers = len(farmers)

        # Plan spawns (avoid consuming more than available)
        target_war_spawns = 0
        if step <= 15 and avail_farmers >= 2 and current_wheat >= 12:
            max_war_spawns = min(avail_farmers // 2, current_wheat // 12)
            target_war_spawns = min(2, max_war_spawns)

        remaining_farmers_after_war = avail_farmers - (2 * target_war_spawns)

        target_farm_spawns = 0
        if step <= 15 and remaining_farmers_after_war >= 2 and current_wheat >= 10:
            max_farm_spawns = min(remaining_farmers_after_war // 2, current_wheat // 10)
            target_farm_spawns = min(2, max_farm_spawns)

        # Allocate farmers to spawn groups and farming
        # Order matters to avoid overlapping assignments
        farmers_to_war_spawn = farmers[:2 * target_war_spawns]
        farmers_to_farm_spawn = farmers[2 * target_war_spawns:
                                        2 * target_war_spawns + 2 * target_farm_spawns]
        farmers_to_farm = farmers[2 * target_war_spawns + 2 * target_farm_spawns:]

        # Warriors go to the Cave (to later attack)
        for w in warriors:
            environment.assign_group(w, "cave")

        # Spawn groups (farmers to spawn new villagers)
        for f in farmers_to_war_spawn:
            environment.assign_group(f, "spawn warrior")
        for f in farmers_to_farm_spawn:
            environment.assign_group(f, "spawn farmer")

        # Remaining farmers stay in farming
        for f in farmers_to_farm:
            environment.assign_group(f, "farm")

        # If there are no farmers or all have been assigned to spawn groups above,
        # there might be nothing else to do for farmers; Warriors already assigned to cave.

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Assign villagers in the Cave into:
        - "attack": Attack the Dragon (for Warriors)
        - "cave": Stay in the Cave (optional, but not used here)
        - "village": Go to the Village (Farmers should return to farming)
        """
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                # All Warriors should attack
                environment.assign_group(c, "attack")
            else:
                # Farmers should go back to the Village
                environment.assign_group(c, "village")