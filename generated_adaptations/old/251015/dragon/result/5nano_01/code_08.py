import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate Farmers and Warriors currently in the Village
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # Wheat available in the Farm (safe access)
        wheat = getattr(getattr(environment, "farm", None), "wheat", 0)

        # 1) Spawn Warriors if possible (prioritize DPS growth)
        # Constraints: need 2 farmers per spawn, 12 wheat per spawn, cap at 2 spawns per step
        max_war_spawns = min(len(farmers) // 2, wheat // 12, 2)
        spawn_warriors = farmers[:2 * max_war_spawns]
        for c in spawn_warriors:
            environment.assign_group(c, "spawn warrior")

        # Update remaining farmers and wheat after warrior spawns
        remaining_farmers = farmers[2 * max_war_spawns:]
        wheat_after_war = wheat - 12 * max_war_spawns

        # 2) Spawn Farmers if possible (to boost future wheat production)
        # Constraints: need 2 farmers per spawn, 10 wheat per spawn, cap at 2 spawns
        max_farm_spawns = min(len(remaining_farmers) // 2, wheat_after_war // 10, 2)
        spawn_farmers = remaining_farmers[:2 * max_farm_spawns]
        for c in spawn_farmers:
            environment.assign_group(c, "spawn farmer")

        # Remaining farmers after farmer spawns go to farming
        final_farmers = remaining_farmers[2 * max_farm_spawns:]
        for c in final_farmers:
            environment.assign_group(c, "farm")

        # 3) All Warriors should go to the Cave to attack
        for c in warriors:
            environment.assign_group(c, "cave")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave: keep Warriors attacking; Farmers return to Village
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")