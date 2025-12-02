# Strategy reasoning and plan (embedded as comments for traceability):
# - Observations from the failed run:
#   - Warriors were not being formed in sufficient numbers; the Dragon remained alive.
#   - Wheat management and spawn decisions were not optimized to produce early offense.
# - Improved adaptation strategy:
#   1) In assign_in_village:
#      - Move all existing Warriors to the cave immediately (consistent with the goal of maximizing
#        offensive force).
#      - The remaining villagers are Farmers. We will intelligently split Farmers into three groups:
#        a) "farm"  : stay in the Village and farm to produce wheat
#        b) "spawn farmer": use two Farmers plus wheat to spawn a new Farmer
#        c) "spawn warrior": use two Farmers plus wheat to spawn a new Warrior
#      - We perform a small optimization over how many Farmers to allocate to farming vs spawning.
#        The objective is to maximize the number of new Warriors spawned this turn (to accelerate
#        Dragon kill), while still maintaining some farming to produce wheat for future spawns.
#      - Dawdling on farming yields fewer Warriors; thus we greedily maximize Warrior spawns per step,
#        breaking ties by choosing a plan that keeps more farming to sustain wheat production.
#      - This approach ensures that, as soon as wheat is available, we spawn extra Warriors and send
#        them to the Cave via assign_in_cave in the next steps.
#   2) In assign_in_cave:
#      - All Warriors should attack (group "attack").
#      - All Farmers should go to the Village (group "village").
#   3) The spawn logic uses current wheat plus the wheat produced by the Farmers allocated to farming
#      this step (5 wheat per farming Farmer). This mirrors the game dynamics more closely than
#      assuming wheat is static.
#
# - Expected outcome:
#   - Faster growth of Warrior numbers early, leading to higher DPS against the Dragon.
#   - Wheat production maintains spawn capability to keep a pipeline of new villagers (and
#     particularly new Warriors) over the 30-turn limit.
#
# - Implementation notes:
#   - We compute the best distribution by iterating farm_count from 0 to F (Farmers in village).
#   - For each choice, we compute how many spawns we can achieve for Farmers and Warriors given
#     wheat = current wheat + 5 * farm_count (from farming this turn).
#   - We pick the plan with the maximum number of Warrior spawns; ties broken by larger farm_count.
#
# The following Python class implements this strategy.

from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate Farmers and Warriors in the Village
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # 1) Move all Warriors to the Cave to prepare for attack
        for c in warriors:
            environment.assign_group(c, "cave")

        # 2) If there are no farmers, nothing more to do
        F = len(farmers)
        if F == 0:
            return

        # 3) Determine the best distribution of farmers into farming/spawn groups
        best_plan = None  # (farm_count, spawn_farmer_count, spawn_warrior_count)
        best_warrior_spawns = -1

        # Current wheat available (pre-spawn); we'll account for farming production in this loop
        current_wheat = getattr(environment.farm, "wheat", 0)

        for farm_count in range(0, F + 1):
            # Farmers allocated to farming this turn
            farming_villagers = farm_count

            # Remaining farmers available for spawning
            spawn_candidates = F - farming_villagers
            # Wheat available for spawning includes wheat produced by farming this turn
            total_wheat = current_wheat + farming_villagers * 5

            # Spawn farmer: needs 2 villagers and 10 wheat
            max_spawns_farmers = min(spawn_candidates // 2, total_wheat // 10)

            # Remaining farmers after farmer-spawns
            remaining_after_farm_spawns = spawn_candidates - 2 * max_spawns_farmers
            # Wheat left after farmer-spawns
            wheat_after_farm_spawns = total_wheat - 10 * max_spawns_farmers

            # Spawn warrior: needs 2 villagers and 12 wheat
            max_spawns_warriors = 0
            if remaining_after_farm_spawns >= 2 and wheat_after_farm_spawns >= 12:
                max_spawns_warriors = min(remaining_after_farm_spawns // 2,
                                          wheat_after_farm_spawns // 12)

            # Choose best plan: maximize Warrior spawns; break ties by more farming (to sustain wheat)
            if max_spawns_warriors > best_warrior_spawns or (
                max_spawns_warriors == best_warrior_spawns and farming_villagers > (best_plan[0] if best_plan else -1)
            ):
                best_warrior_spawns = max_spawns_warriors
                best_plan = (farm_count, 2 * max_spawns_farmers, 2 * max_spawns_warriors)

        # If no plan found (shouldn't happen unless F == 0), default to farming all
        if best_plan is None:
            best_plan = (F, 0, 0)

        farm_count, spawn_farmer_count, spawn_warrior_count = best_plan

        # Build the final groups based on the best plan
        # Spawn farmer villagers come from the initial farmers list
        spawn_farmer_villagers = farmers[:spawn_farmer_count]

        # Spawn warrior villagers come from the next batch after spawn farmers
        spawn_warrior_villagers = farmers[spawn_farmer_count: spawn_farmer_count + spawn_warrior_count]

        farming_villagers = farmers[spawn_farmer_count + spawn_warrior_count:]

        # Apply group assignments
        for c in spawn_farmer_villagers:
            environment.assign_group(c, "spawn farmer")

        for c in spawn_warrior_villagers:
            environment.assign_group(c, "spawn warrior")

        for c in farming_villagers:
            environment.assign_group(c, "farm")

        # Warriors were moved to cave earlier; any unexpected non-Farmer non-Warrior would default to farm
        # (not expected given the data model, but safe-guard if needed)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave: All Warriors go to Attack; Farmers return to Village
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")