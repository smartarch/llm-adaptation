"""
Reasoning and adaptation strategy:

Goal: keep more villagers actively farming (reduce 'damage to the fields' meaning fewer farmers diverted
from farming) while still producing enough warriors to reliably kill the Dragon.

Problems with previous approach:
- It often used too many farmers for spawning warriors early, which lowered the average number of farmers
  working the farm (and resulted in 0 spawned farmers).
- That reduced long-term wheat income and made the village fragile.

New strategy highlights:
1. Always send Warriors in the Village to the Cave (and Warriors in Cave attack) — per requirement.
2. Farmers should remain in the Village. Reserve more farmers to farm when possible:
   - If there are >=4 farmers, reserve 2 farmers to farm each step (better income stability).
   - If there are 3 farmers, reserve 1 farmer.
   - If there are 2 farmers, reserve 1 farmer usually, but allow an early warrior spawn only under
     controlled conditions (to avoid starving the economy).
   - If there is 1 farmer, it farms.
3. Spawning logic:
   - Prefer to spawn farmer pairs when wheat is abundant (sim_wheat >= 20) to increase long-term income.
   - Otherwise prioritize spawning warriors (higher damage) but always keep the reserved farmers farming.
   - Special case for exactly 2 farmers: spawn warrior only if wheat >= 12 AND (we are past a few initial steps
     OR the Dragon still has lots of HP) — this prevents unnecessary early consumption of the only farmer
     who would be producing wheat.
4. Never spawn warriors when the Dragon is nearly dead (hp <= 6) to avoid wasting wheat.
5. Always explicitly assign each component to exactly one group.

This balances short-term aggression with preserving the farming base, raising the average number of farming villagers
and spawning some farmers when wheat is plentiful.

Implementation below.
"""

from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def assign_in_village(self, components, environment, group_ids, step: int):
        # Groups: "farm", "cave", "spawn farmer", "spawn warrior"
        farmers = [c for c in components if getattr(c, "role", "").lower() == "farmer"]
        warriors = [c for c in components if getattr(c, "role", "").lower() == "warrior"]

        # Move all warriors in village to cave (they should be attacking)
        for w in warriors:
            environment.assign_group(w, "cave")

        total_farmers = len(farmers)
        if total_farmers == 0:
            return

        # Read wheat (read-only). Use a local simulated wheat for deciding this step.
        try:
            sim_wheat = int(environment.farm.wheat)
        except Exception:
            sim_wheat = 0

        # Special handling when exactly 2 farmers to avoid starving the farm too early:
        if total_farmers == 2:
            # Conditions to allow spawning a warrior using both farmers:
            # - Have enough wheat (>=12) and
            # - Either we've played a few steps (step > 3) OR Dragon has lots of HP (needs aggression)
            # Otherwise keep both farming to build up wheat.
            if sim_wheat >= 12 and (step > 3 or environment.dragon.hp > 30):
                # Use both to spawn a warrior
                for f in farmers:
                    environment.assign_group(f, "spawn warrior")
            else:
                # Keep both farming
                for f in farmers:
                    environment.assign_group(f, "farm")
            return

        # For 1 farmer: just farm
        if total_farmers == 1:
            environment.assign_group(farmers[0], "farm")
            return

        # For 3 or more farmers:
        # Reserve number of farmers to farm to maintain income:
        # - If >=4 farmers, reserve 2 to farm.
        # - If exactly 3 farmers, reserve 1 to farm.
        if total_farmers >= 4:
            reserve_count = 2
        else:
            reserve_count = 1

        # Assign reserved farmers to farm (take the first reserve_count farmers)
        reserved = farmers[:reserve_count]
        remaining = farmers[reserve_count:]

        for rf in reserved:
            environment.assign_group(rf, "farm")

        # Now we have remaining farmers (in pairs) to consider for spawning.
        # Prefer spawning farmer pairs when wheat is abundant to grow long-term income,
        # otherwise spawn warriors (priority) but keep at least the reserved farmers farming.
        idx = 0
        pairs_available = len(remaining) // 2

        # Spawn farmer pairs first if wheat is abundant (grow economy)
        spawn_farmer_pairs = 0
        if sim_wheat >= 20 and pairs_available > 0:
            # Spawn as many farmer pairs as allowed by wheat
            spawn_farmer_pairs = min(pairs_available, sim_wheat // 10)
            for _ in range(spawn_farmer_pairs):
                if idx + 1 < len(remaining):
                    environment.assign_group(remaining[idx], "spawn farmer")
                    environment.assign_group(remaining[idx + 1], "spawn farmer")
                    idx += 2
                    sim_wheat -= 10

        # Recompute remaining pairs
        pairs_left = (len(remaining) - idx) // 2

        # Spawn warrior pairs next, but avoid spawning if dragon nearly dead
        spawn_warrior_pairs = 0
        if environment.dragon.hp > 6 and pairs_left > 0:
            spawn_warrior_pairs = min(pairs_left, sim_wheat // 12)
            for _ in range(spawn_warrior_pairs):
                if idx + 1 < len(remaining):
                    environment.assign_group(remaining[idx], "spawn warrior")
                    environment.assign_group(remaining[idx + 1], "spawn warrior")
                    idx += 2
                    sim_wheat -= 12

        # Any leftover farmers are assigned to farm
        while idx < len(remaining):
            environment.assign_group(remaining[idx], "farm")
            idx += 1

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # Groups: "attack", "cave", "village"
        # All Warriors -> attack. All Farmers -> return to village (protect the fields).
        for c in components:
            role = getattr(c, "role", "").lower()
            if role == "warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")