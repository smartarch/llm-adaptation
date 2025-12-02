# SmartAdaptation v2 for the Dragon hunt problem.
#
# Reasoning and improved strategy (described here in comments):
#
# Summary of issues with previous attempt:
# - Too few attackers overall (almost no attacking villagers).
# - No spawning occurred because we were too conservative about reserving farmers.
# - Warriors were sent en masse to the Cave and got wiped out by the Dragon's AoE/eat mechanics.
#
# Key observations about game mechanics:
# - Dragon only retaliates when attacked. When it retaliates, its AoE (40%) and eat (20%)
#   affect every villager currently in the Cave. Therefore, keeping many villagers in the Cave
#   during an attack causes heavy casualties.
# - Farmers are the wheat producers and are required to spawn new villagers.
# - Spawning consumes pairs of villagers assigned to a spawn group (2 villagers per spawn).
#
# New strategy goals:
# 1) Protect wheat production: keep most farmers farming so we can accumulate wheat to spawn.
# 2) Spawn more aggressively but safely:
#    - Prioritize spawning Warriors (higher DPS) when wheat allows.
#    - If there are too few farmers to both farm and spawn, allow spawning even if it temporarily
#      reduces farming (but prefer to leave at least one farmer when possible).
# 3) Minimize casualties during Dragon retaliation:
#    - Do NOT send all warriors to the Cave at once. Instead, send a small attack squad per step.
#    - Keep non-attacking warriors in the Village so they are safe and available for later waves.
#    - In the Cave, only assign healthy warriors (hp > 1) to actually attack; retreat very low-HP
#      warriors immediately back to the Village to preserve them.
# 4) Always explicitly assign every available component to exactly one group every step.
#
# Implementation details:
# - We choose a small attack squad per step (ATTACK_SQUAD_SIZE). This reduces the number of villagers
#   exposed to Dragon retaliation while still dealing consistent DPS over multiple steps.
# - Spawning:
#    - If wheat >= 12, spawn as many warrior pairs as is reasonable given farmer count,
#      while trying to leave at least one farmer (unless only 2 farmers exist, in which case
#      we'll allow spawning both to jumpstart warrior production).
#    - If not enough wheat for warriors but wheat >= 10, spawn farmer pairs to increase future wheat production.
# - All farmers are assigned either to "farm" or to a spawn group. Most warriors are kept in the Village
#   (assigned to "farm" to keep them in Village) except the small squad sent to "cave".
#
# Note: The code is defensive about which group IDs are available in group_ids and falls back to safe defaults.

from generated_adaptations.base_classes.dragon import DragonHuntAdaptation
import math

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Configuration: how many warriors to send to attack per step (attack squad).
        # Keep squad small to reduce casualties. Tuneable parameter.
        self.ATTACK_SQUAD_SIZE = 2

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Assign villagers currently in the Village.
        Goals:
        - Keep most farmers farming; use some pairs to spawn when wheat allows.
        - Keep most warriors in Village (safe) and only send a small squad to Cave.
        """
        # Available group names
        has_farm = "farm" in group_ids
        has_cave = "cave" in group_ids
        has_spawn_farmer = "spawn farmer" in group_ids
        has_spawn_warrior = "spawn warrior" in group_ids

        # Partition villagers
        farmers = [c for c in components if getattr(c, "role", "").lower() == "farmer"]
        warriors = [c for c in components if getattr(c, "role", "").lower() == "warrior"]

        # Determine wheat available
        wheat = 0
        try:
            wheat = int(getattr(environment.farm, "wheat", 0))
        except Exception:
            wheat = 0

        # Decide how many warriors to send to the Cave this step (attack squad).
        # Only send up to ATTACK_SQUAD_SIZE and not more than available warriors.
        attack_squad = min(self.ATTACK_SQUAD_SIZE, len(warriors))

        # Choose the healthiest warriors for the squad (prefer higher HP to survive).
        warriors_sorted = sorted(warriors, key=lambda w: getattr(w, "hp", 0), reverse=True)
        squad = warriors_sorted[:attack_squad]
        non_squad = warriors_sorted[attack_squad:]

        # Assign squad members to go to the cave (they will be assigned to attack in assign_in_cave).
        for w in squad:
            target = "cave" if has_cave else ("farm" if has_farm else group_ids[0])
            environment.assign_group(w, target)

        # Assign non-squad warriors to stay in the Village (we use "farm" group as a safe village group).
        for w in non_squad:
            target = "farm" if has_farm else (group_ids[0] if group_ids else "farm")
            environment.assign_group(w, target)

        # Spawning decision for farmers:
        n_farmers = len(farmers)

        # Helper: function to try to assign pairs for a given spawn group and cost per spawn.
        def assign_spawn_pairs(farmer_list, spawn_group_name, cost_per_spawn, max_pairs_allowed):
            assigned = 0
            pairs_assigned = 0
            # We will assign in pairs: two farmers per spawn.
            i = 0
            while i + 1 < len(farmer_list) and pairs_assigned < max_pairs_allowed:
                if wheat >= cost_per_spawn:
                    f1 = farmer_list[i]
                    f2 = farmer_list[i+1]
                    environment.assign_group(f1, spawn_group_name)
                    environment.assign_group(f2, spawn_group_name)
                    # consume wheat for planning purposes (note: environment state is read-only, but
                    # to avoid overcommitting within this step we track locally)
                    nonlocal_wheat = None  # placeholder to satisfy linting in some environments
                    # reduce local wheat
                    # (we update the outer wheat variable by assignment)
                    # But since Python closures require 'nonlocal', we will mutate via list; simpler to just subtract.
                    # We'll just subtract directly from wheat variable in outer scope using 'wheat_local' pattern.
                    # To keep code straightforward, we will manage wheat at module scope below instead.
                    pairs_assigned += 1
                    i += 2
                else:
                    break
            return pairs_assigned

        # Instead of the above helper with closure complications, implement spawn allocation inline.

        # We'll build a list of farmers available for spawn assignment (we'll choose from start of list).
        # To avoid sending ALL farmers away, prefer to leave at least one farmer if possible.
        farmers_for_spawn = list(farmers)  # copy
        farmers_assigned = set()

        # Determine max warrior pairs allowed:
        if n_farmers <= 2:
            # If only 2 farmers, allow 1 pair spawn (use both) if wheat permits, to jumpstart army.
            max_warrior_pairs = 1
        else:
            # Leave at least one farmer to farm: pairs = floor((n_farmers - 1)/2)
            max_warrior_pairs = (n_farmers - 1) // 2

        # Try spawning warrior pairs first if affordable
        warrior_pairs_spawned = 0
        while max_warrior_pairs > 0 and wheat >= 12 and len(farmers_for_spawn) >= 2:
            # Assign two farmers to spawn warrior
            f1 = farmers_for_spawn.pop(0)
            f2 = farmers_for_spawn.pop(0)
            environment.assign_group(f1, "spawn warrior" if has_spawn_warrior else ("farm" if has_farm else group_ids[0]))
            environment.assign_group(f2, "spawn warrior" if has_spawn_warrior else ("farm" if has_farm else group_ids[0]))
            farmers_assigned.update({f1, f2})
            warrior_pairs_spawned += 1
            wheat -= 12
            max_warrior_pairs -= 1

        # If we couldn't/shouldn't spawn warriors but have wheat for farmer spawn, consider spawning farmers
        # Determine how many farmer pairs we can spawn while leaving at least one farmer (if possible).
        # Recompute available farmers for farmer spawn
        remaining_farmers = [f for f in farmers if f not in farmers_assigned]
        if len(remaining_farmers) >= 2:
            if len(remaining_farmers) <= 2:
                max_farmer_pairs = 1
            else:
                max_farmer_pairs = (len(remaining_farmers) - 1) // 2
            farmer_pairs_spawned = 0
            while max_farmer_pairs > 0 and wheat >= 10 and len(remaining_farmers) >= 2:
                f1 = remaining_farmers.pop(0)
                f2 = remaining_farmers.pop(0)
                environment.assign_group(f1, "spawn farmer" if has_spawn_farmer else ("farm" if has_farm else group_ids[0]))
                environment.assign_group(f2, "spawn farmer" if has_spawn_farmer else ("farm" if has_farm else group_ids[0]))
                farmers_assigned.update({f1, f2})
                farmer_pairs_spawned += 1
                wheat -= 10
                max_farmer_pairs -= 1
            remaining_farmers = [f for f in remaining_farmers if f not in farmers_assigned]
        else:
            remaining_farmers = [f for f in remaining_farmers if f not in farmers_assigned]

        # Assign any farmers not assigned to spawn to farm
        for f in farmers:
            if f in farmers_assigned:
                # already assigned to spawn
                continue
            target = "farm" if has_farm else (group_ids[0] if group_ids else "farm")
            environment.assign_group(f, target)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Assign villagers currently in the Cave.
        Goals:
        - Only healthy warriors should attack. Retreat very low-HP warriors back to Village.
        - Farmers in the Cave should be sent back to Village immediately.
        - If no 'attack' group exists, use 'cave' as fallback.
        """
        has_attack = "attack" in group_ids
        has_village = "village" in group_ids
        has_cave = "cave" in group_ids

        for c in components:
            role = getattr(c, "role", "").lower()
            hp = getattr(c, "hp", 0)
            if role == "warrior":
                # Retreat very low HP warriors to village to preserve them (they would die from AoE 1 dmg if hp==1).
                if hp <= 1:
                    target = "village" if has_village else (group_ids[0] if group_ids else "village")
                    environment.assign_group(c, target)
                else:
                    # Healthy warriors attack
                    target = "attack" if has_attack else ("cave" if has_cave else (group_ids[0] if group_ids else "attack"))
                    environment.assign_group(c, target)
            else:
                # Farmers should return to village to continue farming/spawning
                target = "village" if has_village else (group_ids[0] if group_ids else "village")
                environment.assign_group(c, target)