"""
SmartAdaptation for Dragon hunt.

Reasoning and adaptation strategy (described here and implemented below):

Goal:
- Kill the Dragon quickly while keeping enough farmers to produce wheat for spawning new villagers.
- Follow the rule constraints:
    * All Warriors should go to the Cave and attack.
    * All Farmers should remain in the Village to farm or be used for spawning (either farmers or warriors).
    * Every component must be assigned to exactly one group each step.

Observations:
- Warriors: high damage (3), more effective for killing the Dragon. They must be sent to the Cave and put into "attack".
- Farmers: produce wheat (5) and do little damage (1). They are the economy backbone and are required for spawning new villagers.
- Spawning rules: each spawn action consumes wheat (12 for a warrior, 10 for a farmer) and requires pairs of villagers assigned to the respective spawn group. We must allocate farmers into "spawn warrior" and "spawn farmer" groups in pairs.
- Risk: villagers in the Cave can be damaged or eaten by the Dragon; keeping only Warriors in the Cave reduces risk to the farming economy.
- Time limit: 30 steps; faster kill favors creating more Warriors, but creating too many Warriors too quickly can starve wheat production. We therefore balance spawning: keep at least one farmer farming each step; otherwise try to convert spare farmers into Warriors if wheat is abundant. If wheat is low, spawn additional farmers to raise income.

Heuristic Strategy:
1. assign_in_cave:
   - Every Warrior present in the cave -> assign to "attack".
   - Every Farmer present in the cave -> send back to the Village ("village").
   Rationale: Warriors belong in cave attacking; farmers should not remain exposed there.

2. assign_in_village:
   - Every Warrior present in the village -> send to the Cave ("cave") so they can then be put into "attack" on the next cave assignment or immediately if already in cave.
   - Farmers in the village are the candidates for farming or spawning.
     a. Reserve one farmer to always "farm" (if any farmers exist).
     b. With the remaining farmers, prioritize spawning Warriors when there is sufficient wheat:
        - Spawn as many Warriors (pairs of farmers per spawn) as wheat allows, but never consume all farmers (we reserved one to farm).
        - Simulate wheat consumption locally to decide how many Warrior spawns to attempt this step.
     c. If after spawning Warriors there are still spare farmer pairs and wheat >= 10 per spawn, spawn additional Farmers.
     d. Any leftover farmers not used for spawning are assigned to "farm".
   Rationale: Prioritize producing damage (Warriors) but ensure continuous wheat production by keeping at least one farmer farming. Spawning Farmers is used later to scale income when wheat is relatively high but not enough to justify more Warriors.

Notes:
- We cannot modify environment.farm.wheat directly (read-only). We use a local simulated wheat count to decide allocation for this step so that assignment decisions are consistent and deterministic.
- All components are explicitly assigned to a group each call, as required.
"""

from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Assign villagers currently in the Village to groups:
        - "farm"
        - "cave"
        - "spawn farmer"
        - "spawn warrior"

        Strategy implementation described above.
        """
        # Validate group names presence (not strictly required, but useful for clarity)
        # Expected group names: "farm", "cave", "spawn farmer", "spawn warrior"
        # We'll assume these exist in group_ids; otherwise environment.assign_group will still accept them.

        # Separate villagers by role
        farmers = [c for c in components if getattr(c, "role", "").lower() == "farmer"]
        warriors = [c for c in components if getattr(c, "role", "").lower() == "warrior"]

        # 1) Send all warriors in the village to the cave
        for w in warriors:
            environment.assign_group(w, "cave")

        # 2) Decide how many farmers to allocate to spawn groups vs farming
        total_farmers = len(farmers)
        if total_farmers == 0:
            return  # nothing more to assign in village

        # Read available wheat (read-only); simulate consumption locally
        sim_wheat = int(environment.farm.wheat)

        # Reserve one farmer to always farm (if available)
        reserved_for_farm = 1 if total_farmers >= 1 else 0
        farmers_remaining = total_farmers - reserved_for_farm

        # We'll build a list of assignments for farmers
        assignments = []

        # Helper: pop two farmers from farmers list for spawning
        farmer_iter = iter(farmers)

        # Reserve one farmer for farming (take first)
        reserved_farmers = []
        if reserved_for_farm:
            try:
                reserved_farmers.append(next(farmer_iter))
            except StopIteration:
                pass  # shouldn't happen

        # Collect remaining farmer objects
        remaining_farmer_objs = list(farmer_iter)

        # 2a) Spawn Warriors as priority (cost 12 wheat per spawn, needs 2 farmers)
        spawn_warrior_pairs = min(farmers_remaining // 2, sim_wheat // 12)
        # But don't spawn if Dragon is nearly dead (< 6 HP) to avoid wasting wheat and time
        # Estimate simple threshold: if dragon HP <= 6, avoid spawning warriors
        if environment.dragon.hp <= 6:
            spawn_warrior_pairs = 0

        for _ in range(spawn_warrior_pairs):
            if len(remaining_farmer_objs) >= 2:
                f1 = remaining_farmer_objs.pop(0)
                f2 = remaining_farmer_objs.pop(0)
                assignments.append((f1, "spawn warrior"))
                assignments.append((f2, "spawn warrior"))
                sim_wheat -= 12
                farmers_remaining -= 2

        # 2b) Spawn Farmers if there are still spare pairs and wheat allows (cost 10 wheat per spawn)
        spawn_farmer_pairs = min(farmers_remaining // 2, sim_wheat // 10)
        # If wheat is very low (e.g., < 10) we won't spawn farmers
        for _ in range(spawn_farmer_pairs):
            if len(remaining_farmer_objs) >= 2:
                f1 = remaining_farmer_objs.pop(0)
                f2 = remaining_farmer_objs.pop(0)
                assignments.append((f1, "spawn farmer"))
                assignments.append((f2, "spawn farmer"))
                sim_wheat -= 10
                farmers_remaining -= 2

        # 2c) Any leftover farmers (including the reserved one) go to "farm"
        # First assign reserved farmer(s)
        for rf in reserved_farmers:
            environment.assign_group(rf, "farm")

        # Then assign any remaining farmer objects not used for spawning
        for (farmer_obj, group_name) in assignments:
            environment.assign_group(farmer_obj, group_name)

        # Remaining farmers not assigned yet:
        for f in remaining_farmer_objs:
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Assign villagers currently in the Cave to groups:
        - "attack" (Warriors should attack)
        - "cave"   (stay in cave)
        - "village" (go back to village)

        Strategy:
        - All Warriors -> "attack"
        - All Farmers -> "village" (send back to the Village to farm / be used for spawning)
        """
        for c in components:
            role = getattr(c, "role", "").lower()
            if role == "warrior":
                environment.assign_group(c, "attack")
            else:
                # All non-warriors (Farmers) are sent back to village
                environment.assign_group(c, "village")