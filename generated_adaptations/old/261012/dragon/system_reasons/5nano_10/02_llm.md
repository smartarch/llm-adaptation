Strategy and reasoning (descriptive part)

Goal recap:
- Kill the Dragon as fast as possible.
- All Warriors must go to the Cave and attack the Dragon.
- All Farmers stay in the Village (but farmers can farm or spawn new villagers).
- Spawn mechanics: “spawn farmer” and “spawn warrior” allow creating new villagers given 2 villagers assigned to the spawn group and sufficient wheat (10 and 12 respectively).
- The Dragon can damage villagers in Cave each step and can eat one villager randomly.
- We must ensure at least one attack occurs within the first 15 steps.
- We should create a mix of new Farmers and Warriors to maximize damage output over time, while maintaining the constraint that all Warriors eventually attack.

High-level plan:
- Village phase (assign_in_village):
  - Warriors go to the Cave (group “cave”); Farmers stay in Village (we’ll assign them to “farm” by default).
  - To ensure both a source of additional fighters and more wheat-driven spawns, we opportunistically assign some Farmers to “spawn farmer” and “spawn warrior” groups, using current wheat from environment.farm.wheat as a budget. The final assignment for each farmer is exclusive (one final group per farmer).
  - Spawning policy:
    - Try to spawn up to 2 pairs for Farmers (i.e., up to 4 new farmers) per step, constrained by available wheat (10 wheat per pair) and number of Farmers.
    - Then try to spawn up to 2 pairs for Warriors (i.e., up to 4 new Warriors) with remaining wheat and available Farmers not already allocated to spawn Farmer.
  - This approach ensures a growing population of villagers (both Farmers and Warriors) across steps, increasing the chance to kill the Dragon, while keeping all Farmers in the Village.

- Cave phase (assign_in_cave):
  - All Warriors in the Cave should attack the Dragon: assign to group “attack”.
  - All Farmers in the Cave should return to the Village: assign to group “village”.
  - This satisfies the requirement that all Warriors attack and that Farmers stay in the Village.

- Attack timing and guarantee:
  - Because we spawn Warriors in the Village stage (when possible), within a couple of steps there will be at least one Warrior in the Cave to attack. When they arrive in the Cave, assign_in_cave moves them to “attack” immediately, ensuring an attack early (often within the first few steps). This satisfies “The Dragon should be attacked at least once in the first 15 steps.”

- Additional notes:
  - The implementation strictly assigns exactly one group per villager in each stage, per the spec. The spawn logic is designed to be deterministic with respect to the current wheat and farmer counts, so the final assignments are well-defined in one pass per method.

Code (Python) implementing the SmartAdaptation class:

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate farmers and warriors among villagers in the village
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # Final group mapping (one group per component in this step)
        # We will compute spawn allocations first, then assign remaining to farming.
        # We must ensure all Warriors go to the cave (we set them to "cave" here),
        # and Farmers stay in the Village (default to "farm" unless chosen for spawning).

        # Start by scheduling default allocations
        for f in farmers:
            environment.assign_group(f, "farm")
        for w in warriors:
            environment.assign_group(w, "cave")

        # Spawning logic (one step, exclusive groups per villager)
        # Use wheat budget to decide spawn pairs
        available_wheat = int(getattr(environment.farm, "wheat", 0))

        # Number of farmer spawn pairs we can attempt this step
        max_farm_pairs_by_wheat = available_wheat // 10 if available_wheat >= 10 else 0
        max_farm_pairs_by_count = len(farmers) // 2
        sp_farm_pairs = min(2, max_farm_pairs_by_wheat, max_farm_pairs_by_count)

        # Wheat budget after allocating farmer spawns
        wheat_after_farm_spawns = max(0, available_wheat - sp_farm_pairs * 10)

        # Remaining farmers after farmer-spawn allocations
        used_for_farm_spawns = sp_farm_pairs * 2
        remaining_farmers_for_war_spawn = len(farmers) - used_for_farm_spawns

        # Number of warrior spawn pairs we can attempt this step
        max_war_pairs_by_wheat = wheat_after_farm_spawns // 12 if wheat_after_farm_spawns >= 12 else 0
        sp_war_pairs = min(2, max_war_pairs_by_wheat, remaining_farmers_for_war_spawn // 2)

        # Now assign specific farmers to spawn groups
        idx = 0

        # Assign first 2*sp_farm_pairs farmers to "spawn farmer"
        for _ in range(sp_farm_pairs * 2):
            if idx < len(farmers):
                environment.assign_group(farmers[idx], "spawn farmer")
                idx += 1

        # Assign next 2*sp_war_pairs farmers to "spawn warrior"
        for _ in range(sp_war_pairs * 2):
            if idx < len(farmers):
                environment.assign_group(farmers[idx], "spawn warrior")
                idx += 1

        # Remaining farmers (if any) stay in the village to farm
        while idx < len(farmers):
            environment.assign_group(farmers[idx], "farm")
            idx += 1

        # Warriors already set to "cave" above; nothing else to do for them here.

        # Note: The actual spawning consumes wheat inside the environment/game rules.


    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the cave, all Warriors should attack, Farmers return to the Village
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # Warriors attack
        for w in warriors:
            environment.assign_group(w, "attack")

        # Farmers go back to the Village
        for f in farmers:
            environment.assign_group(f, "village")
```