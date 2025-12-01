from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Split villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Strategy: All Warriors should go to the Cave (to attack later)
        for w in warriors:
            environment.assign_group(w, "cave")

        # Farmers should stay in Village by default, but we can spawn new villagers
        # Determine how many spawns we can attempt this step
        avail_farmers = len(farmers)

        # Wheat available for spawning
        wheat = getattr(environment.farm, "wheat", 0)

        # Max possible spawns based on wheat
        max_farm_spawns = wheat // 10
        max_warrior_spawns = (wheat // 12)

        # First, cap spawns by the number of farmers available
        s_farm = min(avail_farmers // 2, max_farm_spawns)

        # Wheat left after farmer-spawns
        wheat_left = wheat - 10 * s_farm
        remaining_farmers_after_farm = avail_farmers - 2 * s_farm

        # Warrior-spawns are limited by remaining farmers and remaining wheat
        s_warrior = min(remaining_farmers_after_farm // 2, wheat_left // 12)

        # Slight early-game boost to ensure some spawns happen in the first 10 steps
        if step <= 10:
            # If we can spawn one more farmer and still have enough farmers and wheat, try it
            if avail_farmers >= 2 and wheat >= 10 and s_farm < avail_farmers // 2:
                s_farm += 1
                wheat_left -= 10

            # Try to spawn one more warrior if possible
            if remaining_farmers_after_farm >= 2 and wheat_left >= 12:
                s_warrior += 1
                wheat_left -= 12

        # Recompute final allocation counts (ensuring non-negative)
        s_farm = max(0, s_farm)
        s_warrior = max(0, s_warrior)

        # Assign specific farmers to groups
        # First 2*s_farm farmers go to "spawn farmer"
        farmers_to_spawn_farm = farmers[: 2 * s_farm]
        # Next 2*s_warrior farmers go to "spawn warrior"
        start_warrior = 2 * s_farm
        farmers_to_spawn_warrior = farmers[start_warrior: start_warrior + 2 * s_warrior]
        # The rest stay in the farm (Village)
        farmers_to_farm = farmers[start_warrior + 2 * s_warrior:]

        for f in farmers_to_spawn_farm:
            environment.assign_group(f, "spawn farmer")
        for f in farmers_to_spawn_warrior:
            environment.assign_group(f, "spawn warrior")
        for f in farmers_to_farm:
            environment.assign_group(f, "farm")

        # Note: Warriors have already been moved to the cave above.
        # There is no need to assign any farmers to stay in village explicitly here beyond "farm"/spawn groups.

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave, decide who attacks and who stays
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                # Warriors should attack the Dragon
                environment.assign_group(c, "attack")
            else:
                # Farmers should go back to the Village
                environment.assign_group(c, "village")