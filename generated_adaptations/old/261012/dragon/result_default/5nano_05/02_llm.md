Reasoning and adaptation strategy

Goal and constraints:
- All Warriors should head to the Cave and attack the Dragon.
- All Farmers should stay in the Village to farm wheat or participate in spawning new villagers (both Farmers and Warriors are needed).
- Spawns are determined by two villagers assigned to a spawn group plus a wheat cost (10 for Farmer spawn, 12 for Warrior spawn). Spawns create new Farmers/Warriors, respectively.
- The Dragon can attack back; the game ends if the Dragon dies or if 30 steps elapse.

Strategy overview:
- In the village, keep Farmers primarily in farming, but opportunistically use some Farmers to trigger spawns so the population grows and wheat production accelerates in future steps.
- Spawn planning should be conservative and deterministic to avoid over-committing villagers:
  1) First allocate as many Farmer-spawn opportunities as possible, using pairs of Farmers and 10 wheat per spawn (limited by available Farmers and wheat).
  2) With the remaining Farmers, allocate Warrior-spawn opportunities using pairs of Farmers and 12 wheat per spawn (limited by remaining Farmers and wheat).
  3) The rest of Farmers stay in the village farming.
  4) Warriors always go to the cave to attack the Dragon.
- In the cave, move Farmers to the village (they will head back later to farm/spawn) and send Warriors to attack the Dragon. This aligns with the rule that all Warriors should attack and all Farmers should stay in the Village (or go back from the Cave to Village as needed).

Implementation notes:
- assign_in_village:
  - Split villagers by role (Farmer vs Warrior).
  - Compute spawn counts conservatively using current wheat: spawns from Farmers (10 wheat each) first, then spawns from remaining Farmers for Warrior spawns (12 wheat each).
  - Assign exact components to: "spawn farmer", "spawn warrior", or "farm".
  - All Warriors in village are assigned to the "cave" group (to head to cave).
- assign_in_cave:
  - Warriors -> "attack" (attack the Dragon).
  - Farmers -> "village" (go back to the Village).

This approach emphasizes growing the population to boost future wheat production and to increase overall offensive power while ensuring Warriors contribute immediately by attacking the Dragon.

Python code

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate Farmers and Warriors in the Village
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Current farm wheat
        wheat = 0
        if hasattr(environment, "farm") and hasattr(environment.farm, "wheat"):
            wheat = environment.farm.wheat

        # Spawn planning: first Farmer-spawns (2 farmers + 10 wheat per spawn)
        spawn_farmer_slots = min(len(farmers) // 2, int(wheat // 10))
        spawn_farmer_count_paired = spawn_farmer_slots * 2
        wheat_after_farmer_spawns = wheat - spawn_farmer_slots * 10

        # Then Warrior-spawns (2 farmers + 12 wheat per spawn) with remaining farmers
        remaining_farmers_for_warrior = len(farmers) - spawn_farmer_count_paired
        spawn_warrior_slots = min(remaining_farmers_for_warrior // 2, int(wheat_after_farmer_spawns // 12))
        spawn_warrior_count_paired = spawn_warrior_slots * 2

        # Farmers left to farm
        farmers_in_farm_group = len(farmers) - spawn_farmer_count_paired - spawn_warrior_count_paired

        # Assign Farmers to their groups
        i = 0
        for f in farmers:
            if i < spawn_farmer_count_paired:
                environment.assign_group(f, "spawn farmer")
            elif i < spawn_farmer_count_paired + spawn_warrior_count_paired:
                environment.assign_group(f, "spawn warrior")
            else:
                environment.assign_group(f, "farm")
            i += 1

        # Assign Warriors to cave (they will head to Cave)
        for w in warriors:
            environment.assign_group(w, "cave")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave: Warriors should attack, Farmers should go back to Village
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```