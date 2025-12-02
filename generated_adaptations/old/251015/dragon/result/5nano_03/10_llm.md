```py
# Reasoning and adaptation strategy (embedded as comments in the code)
#
# Goal: Further reduce the number of turns to kill the Dragon while keeping the core rules:
# - All Warriors must go to the Cave and attack the Dragon.
# - Farmers stay in the Village to farm or spawn new villagers.
# - Spawning rules:
#     - spawn farmer: for every two villagers assigned to this group and 10 wheat, a new Farmer is spawned.
#     - spawn warrior: for every two villagers assigned to this group and 12 wheat, a new Warrior is spawned.
# - The Dragon can retaliate each step; we want to avoid heavy population loss in the Cave.
#
# Improvements over prior versions:
# - Aggressive yet controlled spawning in the Village to accelerate DPS growth while preserving wheat flow.
# - Maintain at least one Farmer farming whenever possible to sustain wheat production for future spawns.
# - Dynamically choose spawn allocations (spawn farmer vs spawn warrior) based on current counts of Farmers and Wheat.
# - Spawn decisions are deterministic and depend on the current environment state (environment.farm.wheat).
#
# Strategy details:
# - Move all Warriors to the Cave (as required).
# - In the Village, compute:
#     F = number of Farmers, W = current Wheat (environment.farm.wheat if available).
# - Determine how many Farmers we can assign to "spawn farmer" (spf) this step:
#     spf = min(2, F//2, W//10)
# - After allocating spf*2 Farmers to "spawn farmer", compute how many additional Farmers can be allocated to "spawn warrior"
#     swp = min(3, (F - spf*2)//2, (W - spf*10)//12)
# - To avoid starving farming, ensure at least one Farmer remains for farming when possible:
#     - If after choosing spf and swp there are 0 or 1 Farmers left, back off:
#         - If possible, reduce spf by 1 to free two Farmers for farming.
#         - Recompute swp accordingly.
# - Assign Farmers in a deterministic order:
#     first 2*spf -> "spawn farmer"
#     next 2*swp -> "spawn warrior"
#     the remainder -> "farm"
# - In the Cave, send Warriors to "attack" and Farmers to "village".
#
# This approach aims for earlier Dragon damage by increasing Warrior counts earlier while maintaining wheat generation for continued spawns.

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

        # 2) Spawning plan for Farmers (aggressive but controlled)
        F = len(farmers)
        W = 0
        if hasattr(environment, "farm") and hasattr(environment.farm, "wheat"):
            W = environment.farm.wheat

        # Compute maximum possible spawns this step
        max_spf = min(2, F // 2, W // 10) if W >= 10 else 0

        # Decide spf (spawn farmer) with a slight step-based preference for early steps
        if max_spf > 0:
            # Early steps lightly limit spawns to keep farming alive; later steps allow full spf
            spf = 1 if step < 5 else max_spf
            spf = min(spf, max_spf)
        else:
            spf = 0

        spf2 = spf * 2  # number of Farmers allocated to "spawn farmer"
        wheat_after_spf = max(0, W - spf * 10)
        remaining_farmers_after_spf = F - spf2

        # Compute possible swp (spawn warrior) after allocating spf
        max_spw = min(3, remaining_farmers_after_spf // 2, wheat_after_spf // 12) if wheat_after_spf >= 12 else 0
        swp = max_spw
        swp2 = swp * 2

        # Constraint: leave at least one Farmer for farming if possible
        if F - spf2 - swp2 < 1 and swp > 0:
            swp -= 1
            swp2 = swp * 2
            wheat_after_spf = max(0, wheat_after_spf - 12)
            remaining_farmers_after_spf = F - spf2
            max_spw = min(3, remaining_farmers_after_spf // 2, wheat_after_spf // 12) if wheat_after_spf >= 12 else 0
            swp = max_spw
            swp2 = swp * 2

        # If still too few farmers left for farming, consider backing off spf by 1 if possible
        if F - spf2 - swp2 < 1 and spf > 0:
            spf -= 1
            spf2 = spf * 2
            wheat_after_spf = max(0, W - spf * 10)
            remaining_farmers_after_spf = F - spf2
            max_spw = min(3, remaining_farmers_after_spf // 2, (wheat_after_spf) // 12) if wheat_after_spf >= 12 else 0
            swp = max_spw
            swp2 = swp * 2

        # Assign groups to farmers in deterministic order
        for idx, f in enumerate(farmers):
            if idx < spf2:
                environment.assign_group(f, "spawn farmer")
            elif idx < spf2 + swp2:
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
```