"""
 adaptation strategy reasoning (embedded as comments in code):
 
 Task recap:
 - Two villager types: Farmers (HP 4, produce 5 wheat when farming, attack for 1) and Warriors (HP 6, produce 2 wheat when farming, attack for 3).
 - All Warriors should go to the Cave, then attack the Dragon from there.
 - All Farmers should stay in the Village and either farm or help spawn new villagers.
 - Spawning rules (in Village):
     * spawn farmer: for every two villagers assigned to group "spawn farmer" and with 10 wheat, one new Farmer is spawned.
     * spawn warrior: for every two villagers assigned to group "spawn warrior" and with 12 wheat, one new Warrior is spawned.
 - Dragon dynamics and win/lose conditions are simulation concerns; our strategy focuses on group assignment logic.
 - The environment provides:
     * environment.farm.wheat: current wheat amount (read-only for us, wheat consumption is handled by the simulator when a spawn happens)
     * environment.dragon.hp: Dragon HP (read-only)
 - We must implement a greedy but safe spawning plan in assign_in_village to accelerate population growth when wheat allows, while keeping enough Farmers farming to generate wheat for future spawns.
 - In assign_in_cave, we keep Warriors attacking the Dragon (group "attack") and move Farmers back to the Village (group "village") so they can farm or spawn.

 Strategy details implemented in code:
 - In assign_in_village:
     1) Move all Warriors to group "cave" so they head toward the Dragon (to be in future steps in "attack" group when in cave).
     2) For Farmers, use a greedy spawning plan:
         - Let n_farmers be the number of Farmers in the village.
         - Compute spawns_farm = min(n_farmers // 2, wheat // 10). This many new Farmers can be spawned this step if we allocate 2*spawns_farm Farmers to the "spawn farmer" group.
         - Move the first 2*spawns_farm Farmers to the "spawn farmer" group.
         - Remaining wheat is wheat_remaining = wheat - spawns_farm * 10.
         - Compute spawns_warrior = min((n_farmers - 2*spawns_farm) // 2, wheat_remaining // 12).
         - Move the next 2*spawns_warrior Farmers to the "spawn warrior" group.
         - All remaining Farmers are assigned to the "farm" group (they will farm this step).
     3) This greedy approach tries to spawn as many villagers as possible given wheat and available Farmers, while keeping some Farmers to continue farming for future wheat.
 - In assign_in_cave:
     - Assign all Warriors to "attack" (they will attack Dragon).
     - Assign all Farmers to "village" (they should go back to the Village to farm or spawn).
 - This adheres to the rule that all Warriors go to the Cave and all Farmers stay in the Village as much as possible.

 Note:
 - Spawns happen automatically by the simulator after each step based on the groups "spawn farmer" and "spawn warrior" and the wheat amounts available. Our code ensures we respect the required grouping for spawns and that the wheat resources are consumed by the simulator accordingly.
 - All group names used below must appear exactly as provided:
     Village groups: "farm", "cave", "spawn farmer", "spawn warrior"
     Cave groups: "attack", "cave", "village"

"""

from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Assign all Warriors to go to the Cave (to join the attack later)
        villagers = list(components)

        # Gather all Warriors and Farmers from the village
        farmers = [c for c in villagers if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in villagers if getattr(c, "role", None) == "Warrior"]

        # 1) Move all Warriors to the cave group
        for w in warriors:
            environment.assign_group(w, "cave")

        # 2) Spawn strategy for Farmers (greedy but safe)
        # Wheat available now
        wheat = getattr(environment.farm, "wheat", 0)

        n_farmers = len(farmers)

        # We will assign two farmers to spawn farmer group as many times as possible given wheat
        spawns_farm = min(n_farmers // 2, wheat // 10) if n_farmers >= 2 else 0

        # Prepare lists to assign groups
        # We'll take first 2*spawns_farm farmers to the spawn_farm group
        spawn_farm_members = farmers[: 2 * spawns_farm]
        remaining_after_farm_spawns = farmers[2 * spawns_farm :]

        # Now consider spawning warriors with remaining farmers and remaining wheat
        wheat_after_farm = wheat - spawns_farm * 10
        n_remaining = len(remaining_after_farm_spawns)
        spawns_warrior = min(n_remaining // 2, wheat_after_farm // 12) if n_remaining >= 2 else 0

        spawn_war_members = remaining_after_farm_spawns[: 2 * spawns_warrior]
        remaining_after_war_spawns = remaining_after_farm_spawns[2 * spawns_warrior :]

        # The rest of Farmers go to farming group
        farm_group_members = remaining_after_war_spawns

        # 3) Assign groups
        for f in spawn_farm_members:
            environment.assign_group(f, "spawn farmer")
        for f in spawn_war_members:
            environment.assign_group(f, "spawn warrior")
        for f in farm_group_members:
            environment.assign_group(f, "farm")

        # If there are any Farmers that weren't included (edge cases), ensure they get a farm assignment
        # (This can happen if there were no spawns or lists were misaligned)
        # Note: all Farmers should be accounted for in one of the above groups.

        # Ensure there are no stray assignments for Farmers
        # (No explicit action needed; any Farmer not assigned above remains ungrouped,
        # but we assigned all farmers to one of the groups above.)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In Cave: All Warriors should attack the Dragon.
        # All Farmers should go back to the Village.
        for comp in components:
            role = getattr(comp, "role", None)
            if role == "Warrior":
                environment.assign_group(comp, "attack")
            else:
                # Farmers go to Village
                environment.assign_group(comp, "village")