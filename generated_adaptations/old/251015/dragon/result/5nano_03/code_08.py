# Reasoning and adaptation strategy (embedded as comments in the code)
#
# Goal: Kill the Dragon as fast as possible within the game's 30-step limit.
# Constraints recap:
# - Warriors must go to the Cave and attack the Dragon.
# - Farmers stay in the Village to farm or spawn new villagers.
# - Spawning rules:
#     - spawn farmer: for every two villagers assigned to this group and 10 wheat, a new Farmer is spawned.
#     - spawn warrior: for every two villagers assigned to this group and 12 wheat, a new Warrior is spawned.
# - The Dragon can retaliate each step: with prob 0.4, it damages every villager in the Cave by 1 HP,
#   with prob 0.2 it eats one random villager in the Cave. Villagers reduced by these effects may die.
# - All Warriors should eventually be in the Cave; Farmers should primarily farm/spawn in the Village.
#
# Strategy overview:
# - Move all Warriors to the Cave each village step (as required).
# - In the Village, spawn farming capacity first to ensure a steady wheat supply (which enables future spawns).
# - Introduce a conservative but progressive spawning plan:
#     - Allow up to 2 "spawn farmer" actions per step, limited by available Farmers and Wheat.
#     - After allocating farmers to spawn farmers, optionally allocate some Farmers to "spawn warrior" to reinforce DPS, but cap Warrior spawns to avoid overcrowding the Cave and excessive risk from Dragon retaliation.
# - This aims to balance rapid DPS growth (via additional Warriors) with sustained Wheat production (via Farmers) and a controlled exposure risk in the Cave.
#
# Implementation notes:
# - We compute how many Farmers and how much Wheat we have in the Village.
# - We compute spf (spawn farmers) and swp (spawn warriors) for this step with simple caps:
#     spf up to 2 per step, limited by F//2 and W//10.
#     swp up to 3 per step, limited by (F - 2*spf)//2 and (W - 10*spf)//12.
# - We assign the first 2*spf Farmers to "spawn farmer", the next 2*swp Farmers to "spawn warrior",
#   and the remaining Farmers to "farm".
# - Warriors are always sent to the Cave in assign_in_village, and Farmers in the Cave are sent back to the Village in assign_in_cave.
#
# This approach is designed to be deterministic, incremental, and responsive to the current wheat stock and
# farmer count, while maintaining the core rule that Warriors attack and Farmers farm/spawn.

from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate villagers by role in the village context
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # 1) All Warriors go to the Cave (as required)
        for w in warriors:
            environment.assign_group(w, "cave")

        # 2) Spawning plan for farmers (conservative but progressive)
        F = len(farmers)
        W = 0
        if hasattr(environment, "farm") and hasattr(environment.farm, "wheat"):
            W = environment.farm.wheat

        spf = 0  # number of "spawn farmer" actions this step (0 or up to 2)
        swp = 0  # number of "spawn warrior" actions this step (0 up to 3)

        # Compute max possible spawns this step given constraints
        max_spf = min(2, F // 2, W // 10) if W >= 10 else 0
        if max_spf < 0:
            max_spf = 0

        # Step-based tweak: allow at most 2 spf per step, but respect resource limits
        if max_spf >= 1:
            # Simple step-based ramp: in early steps, be slightly more conservative,
            # in later steps, allow full max_spf
            if step < 5:
                spf = 1
            else:
                spf = max_spf

        spf = min(spf, max_spf)
        spf2 = spf * 2  # number of Farmers allocated to "spawn farmer"

        # Wheat remaining after farmer spawns
        wheat_after_spf = max(0, W - spf * 10)

        # Remaining Farmers after farmer spawns
        remaining_farmers_after_spf = F - spf2

        # Maximum possible Warrior spawns after farmer spawns
        max_spw = min(3, remaining_farmers_after_spf // 2, wheat_after_spf // 12) if wheat_after_spf >= 12 else 0
        swp = max_spw
        swp2 = swp * 2  # number of Farmers allocated to "spawn warrior"

        # Assign groups to farmers in deterministic order
        for idx, f in enumerate(farmers):
            if idx < spf2:
                environment.assign_group(f, "spawn farmer")
            elif swp > 0 and idx < spf2 + swp2:
                environment.assign_group(f, "spawn warrior")
            else:
                environment.assign_group(f, "farm")

        return

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the cave, send Warriors to attack, Farmers back to the Village
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")