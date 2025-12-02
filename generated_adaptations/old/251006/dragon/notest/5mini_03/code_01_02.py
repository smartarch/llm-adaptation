# SmartAdaptation for the Dragon hunt problem.
#
# Reasoning and strategy (described here in comments as required):
#
# Goal summary:
# - Kill the Dragon quickly (win if dragon hp <= 0 within 30 steps).
# - Warriors are best at dealing damage (3 dmg each) and should be the ones attacking in the Cave.
# - Farmers produce wheat (5 each per step) and are used to create new villagers.
# - Spawning requires 2 villagers assigned to the spawn group + wheat cost (10 for farmer, 12 for warrior).
# - We must explicitly assign every component each step to the desired group.
#
# Strategy overview:
# 1) In the Village:
#    - Ensure all Warriors in the Village move to the Cave (group "cave") so they can attack next step.
#    - Keep the majority of Farmers farming to generate wheat, but use up to one spawn pair per step
#      (two Farmers) if wheat allows to grow the force gradually. Prioritize spawning Warriors when
#      wheat >= 12 and we have at least two spare Farmers, otherwise spawn Farmers when wheat >= 10.
#    - Reserve at least one Farmer farming (never send all farmers to spawn) so wheat production continues.
#    - If group names provided do not include the desired spawn groups, fallback to assigning farmers to "farm".
#
#    Rationale: spawning at most one pair per step balances short-term farming (wheat income) vs long-term
#    damage output (more Warriors). Prioritizing warrior spawn accelerates DPS when sufficient wheat exists.
#
# 2) In the Cave:
#    - All Warriors attack (group "attack") as they are the primary damage dealers.
#    - Any Farmers found in the Cave are sent back to the Village (group "village") because farmers should farm/spawn.
#    - We do not attempt complex HP-based retreats here to follow the user's instruction that all Warriors go to the Cave and attack.
#
# Implementation notes:
# - We consult environment.farm.wheat to decide whether spawning is affordable.
# - Each component is explicitly assigned to exactly one group every call.
# - The code checks that target group names exist in group_ids and falls back to safe defaults if not.
#
# The class below implements the described strategy.

from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        components: list of villagers currently in Village
        environment.farm.wheat available for spawn decisions
        group_ids: list of valid group names (must use exactly names given)
        """
        # Validate required groups (we will fallback to safe defaults if missing)
        has_farm = "farm" in group_ids
        has_cave = "cave" in group_ids
        has_spawn_farmer = "spawn farmer" in group_ids
        has_spawn_warrior = "spawn warrior" in group_ids

        # Partition villagers by role
        farmers = [c for c in components if getattr(c, "role", "").lower() == "farmer"]
        warriors = [c for c in components if getattr(c, "role", "").lower() == "warrior"]

        # First, send all warriors to the cave (so they can attack)
        for w in warriors:
            # fallback to "farm" if "cave" not present (shouldn't happen per spec)
            target = "cave" if has_cave else ("farm" if has_farm else group_ids[0])
            environment.assign_group(w, target)

        # Decide spawning using farmers.
        wheat = 0
        try:
            wheat = int(getattr(environment.farm, "wheat", 0))
        except Exception:
            wheat = 0

        n_farmers = len(farmers)
        # Reserve at least one farmer to farm if possible
        reserve = 1 if n_farmers >= 1 else 0
        available_for_spawn = max(0, n_farmers - reserve)

        # We'll allow at most one spawn pair per step (2 villagers).
        spawn_pair_size = 2
        spawned_assigned = 0  # how many farmers we've assigned to a spawn group

        # Prioritize spawning a warrior if we can afford it and have at least 2 farmers available
        if available_for_spawn >= spawn_pair_size and wheat >= 12 and has_spawn_warrior:
            # assign two farmers to spawn warrior
            for f in farmers[:spawn_pair_size]:
                environment.assign_group(f, "spawn warrior")
                spawned_assigned += 1
        # Else, try spawning a farmer if affordable
        elif available_for_spawn >= spawn_pair_size and wheat >= 10 and has_spawn_farmer:
            for f in farmers[:spawn_pair_size]:
                environment.assign_group(f, "spawn farmer")
                spawned_assigned += 1

        # Assign remaining farmers to farm
        # Make sure we don't reassign already assigned farmers (spawned_assigned)
        for f in farmers[spawned_assigned:]:
            target = "farm" if has_farm else (group_ids[0] if group_ids else "farm")
            environment.assign_group(f, target)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        components: list of villagers currently in Cave
        For each component assign to "attack" (warriors) or "village" (farmers).
        """
        has_attack = "attack" in group_ids
        has_village = "village" in group_ids
        has_cave = "cave" in group_ids  # fallback option to stay in cave without attacking

        for c in components:
            role = getattr(c, "role", "").lower()
            # Warriors attack
            if role == "warrior":
                target = "attack" if has_attack else ("cave" if has_cave else (group_ids[0] if group_ids else "attack"))
                environment.assign_group(c, target)
            else:
                # Farmers should return to village to farm/spawn
                target = "village" if has_village else (group_ids[0] if group_ids else "village")
                environment.assign_group(c, target)