Reasoning and improved adaptation strategy

Goal and lessons
- We want to push the kill as early as possible while respecting the constraints: all Warriors must go to the Cave to attack, all Farmers stay in the Village (except for spawning groups), and spawns consume wheat.
- The Dragon’s AoE hit in the Cave (40% chance to deal 1 damage to every villager in the Cave) means that larger Cave populations increase risk. However, surviving to accumulate DPS quickly is typically worth the risk, since DPS scales linearly with the number of attacking Warriors (3 damage each).
- The prior approach already ramped DPS, but we can push for even faster kills by aggressively spawning Warriors as soon as wheat and farmers allow, and by making spawning decisions more deterministic (less step-dependent gating). This should reduce the number of turns to kill on average, provided we keep a reasonable balance to avoid excessive casualties from the Dragon’s AoE.

Key improvements
- Aggressive but bounded spawning: Always try to spawn up to 2 Warriors per step, subject to having at least 4 Farmers to sacrifice (2 per Warrior) and at least 12 Wheat per Warrior to spawn (cumulative). This ramp accelerates DPS quickly in the early game.
- Efficient use of wheat: After allocating 2*Warriors to spawn Warrior, use any remaining wheat to spawn up to 2 Farmers (subject to available Farmers), ensuring we keep Wheat usage efficient and still generate extra villagers for future spawns.
- Always send all Warriors to the Cave to maximize early DPS; Farmers stay in Village, except those in spawn groups.
- No reliance on step-based bonuses: Remove explicit step-based bumps and rely on consistent, maximal allowed spawns per step given resources.

How this satisfies the requirements
- Dragon is killed faster via higher early DPS.
- Attack occurs in the first 15 steps because Warriors are moved to the Cave immediately and attack as soon as possible.
- All Warriors go to the Cave, and all Farmers stay in the Village (except for spawning groups).
- Spawns generate extra Farmers and Warriors to increase DPS over time.
- All Warriors attack once in the Cave.
- The Cave contains a large share of Warriors early, aiding DPS, while spawning groups provide additional future Warriors.

Python code

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Strategy: All Warriors should go to the Cave (to attack later)
        for w in warriors:
            environment.assign_group(w, "cave")

        # Wheat available for spawning
        wheat = getattr(environment.farm, "wheat", 0)

        # Spawn as many Warriors as possible this step, bounded to 2,
        # and only if we have enough Farmers to sacrifice (2 farmers per Warrior)
        max_possible_warrior_spawns = min(len(farmers) // 2, wheat // 12, 2)
        s_warrior = max_possible_warrior_spawns

        # After allocating Warrior spawns, recompute remaining farmers and wheat
        remaining_farmers = len(farmers) - 2 * s_warrior
        wheat_left_after_warriors = wheat - 12 * s_warrior

        # Spawn up to 2 Farmers this step if possible
        max_possible_farm_spawns = min(remaining_farmers // 2, wheat_left_after_warriors // 10, 2)
        s_farm = max_possible_farm_spawns

        # Assign specific farmers to groups
        idx = 0
        # First 2*s_warrior farmers -> "spawn warrior"
        farmers_to_spawn_warrior = farmers[idx: idx + 2 * s_warrior]
        idx += 2 * s_warrior

        # Next 2*s_farm farmers -> "spawn farmer"
        farmers_to_spawn_farm = farmers[idx: idx + 2 * s_farm]
        idx += 2 * s_farm

        # The remaining farmers stay in Farm (Village)
        farmers_to_farm = farmers[idx:]

        for f in farmers_to_spawn_warrior:
            environment.assign_group(f, "spawn warrior")
        for f in farmers_to_spawn_farm:
            environment.assign_group(f, "spawn farmer")
        for f in farmers_to_farm:
            environment.assign_group(f, "farm")

        # Warriors are already in the cave; no explicit movement needed here.

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave, decide who attacks and who stays
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                # Warriors should attack the Dragon
                environment.assign_group(c, "attack")
            else:
                # Farmers should go back to the Village
                environment.assign_group(c, "village")
```