import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Gather villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # 1) Move all Warriors to the cave (they will be in cave to be attacked)
        for w in warriors:
            if "cave" in group_ids:
                environment.assign_group(w, "cave")

        # 2) Spawn planning for Farmers (stay in Village)
        # Use available wheat to spawn new Farmers and Warriors.
        wheat = getattr(environment.farm, "wheat", 0)

        # Determine how many farmer-spawns we can perform (2 farmers per spawn, needs 10 wheat)
        spawn_farmer_count = 0
        if len(farmers) >= 2 and wheat >= 10:
            spawn_farmer_count = min(len(farmers) // 2, wheat // 10)

        # Assign first 2*spawn_farmer_count farmers to "spawn farmer"
        idx = 0
        for i in range(2 * spawn_farmer_count):
            if idx < len(farmers) and "spawn farmer" in group_ids:
                environment.assign_group(farmers[idx], "spawn farmer")
                idx += 1
        wheat -= spawn_farmer_count * 10  # Wheat consumed by farmer spawns

        # 3) Now consider spawning Warriors (2 farmers per spawn, needs 12 wheat)
        remaining_farmers = farmers[idx:]
        spawn_warrior_count = 0
        if len(remaining_farmers) >= 2 and wheat >= 12:
            spawn_warrior_count = min(len(remaining_farmers) // 2, wheat // 12)

        # Assign next 2*spawn_warrior_count farmers to "spawn warrior"
        for i in range(2 * spawn_warrior_count):
            fi = idx + i
            if fi < len(farmers) and "spawn warrior" in group_ids:
                environment.assign_group(farmers[fi], "spawn warrior")
        idx += 2 * spawn_warrior_count  # advance index

        # 4) Remaining farmers go to farming in Village
        for j in range(idx, len(farmers)):
            if "farm" in group_ids:
                environment.assign_group(farmers[j], "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In Cave:
        # - Warriors should attack the Dragon
        # - Farmers should stay in Village
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                if "attack" in group_ids:
                    environment.assign_group(c, "attack")
                else:
                    # Fallback: stay in Cave if no explicit attack group
                    if "cave" in group_ids:
                        environment.assign_group(c, "cave")
            else:
                # Farmers stay in Village
                if "village" in group_ids:
                    environment.assign_group(c, "village")