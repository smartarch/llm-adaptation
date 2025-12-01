Reasoning and improved adaptation strategy

Goal: further reduce the number of turns to kill the Dragon by making the early phase of the game more aggressive in dealing damage, while still avoiding wheat starvation that would stall spawns.

Key ideas:
- Kill speed depends on DPS in the cave (number of Warriors attacking) and how quickly we can spawn more attackers via the village spawns.
- Prioritize having Warriors attack as soon as possible to maximize damage in early turns. However, keep enough Farmers to sustain wheat production so we can continue spawning attackers if needed.
- Use a dynamic, step-aware policy:
  - Early/mid game (more steps left and dragon HP high): aggressive DPS. Spawn as many Warriors as possible (subject to leaving a small farming base) to maximize early damage.
  - Later game or when wheat is tight: balance spawns to also maintain wheat production (spawn some Farmers if possible) so you can sustain future spawns and possibly finish the dragon sooner.
- In the cave, all Warriors attack the Dragon; Farmers in the cave are moved back to the Village.

Adaptation strategy details:
- In assign_in_village:
  - Compute F (farmers) and W (wheat), dragon_hp, and steps_left (30 - step).
  - If steps_left > 9 and dragon_hp > 25 (early/mid game with relatively high HP): aggressive DPS policy.
    - Spawn as many Warriors as possible by using pairs of Farmers (leave at least a small farming base, e.g., 2-3 farmers if possible) and up to wheat constraints (12 wheat per Warrior pair).
    - Then use any remaining Farmers and Wheat to spawn Farmers (10 wheat per Farmer pair).
    - Remaining Farmers go to farm.
  - Else (late game or wheat limited): balanced policy.
    - Try to spawn Warriors while keeping a small farming base (e.g., ensure some Farmers remain to farm if possible).
    - Use remaining Farmers and Wheat to spawn Farmers as available.
    - Remaining Farmers go to farm.
  - All Warriors in village are moved to the cave (group "cave").
- In assign_in_cave:
  - Warriors attack (group "attack").
  - Farmers return to Village (group "village").

This approach aims to maximize early damage to the Dragon while ensuring wheat production remains sufficient to sustain future spawns, potentially reducing the total number of steps to win.

Python implementation

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate villagers by role in the village
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        F = len(farmers)
        W = getattr(environment.farm, "wheat", 0)
        dragon_hp = getattr(environment.dragon, "hp", 0)
        steps_left = max(0, 30 - step)

        # Strategy decision: aggressive early DPS vs balanced/late-game
        aggressive = (steps_left > 9) and (dragon_hp > 25)

        if aggressive:
            # Aggressive DPS: spawn as many Warriors as possible, keep a small farming base
            # Leave at least 2 farmers for farming if possible
            leave_for_farming = 2 if F >= 2 else 0
            max_warrior_pairs_by_farmers = max(0, (F // 2) - (1 if F >= 2 else 0))
            warrior_pairs = min(max_warrior_pairs_by_farmers, W // 12)
            spawn_warrior_count = 2 * warrior_pairs

            remaining_farmers_after_warrior = F - spawn_warrior_count
            remaining_wheat_after_warrior = W - 12 * warrior_pairs

            farm_pairs = min(remaining_farmers_after_warrior // 2, remaining_wheat_after_warrior // 10)
            spawn_farm_count = 2 * farm_pairs

            idx = 0
            for f in farmers:
                if idx < spawn_warrior_count:
                    environment.assign_group(f, "spawn warrior")
                elif idx < spawn_warrior_count + spawn_farm_count:
                    environment.assign_group(f, "spawn farmer")
                else:
                    environment.assign_group(f, "farm")
                idx += 1
        else:
            # Balanced/late-game spawning: keep a small farming base if possible
            keep_farming = 3 if F >= 3 else F
            available_for_spawns_farmers = F - keep_farming

            warrior_pairs = 0
            if available_for_spawns_farmers >= 2:
                warrior_pairs = min(available_for_spawns_farmers // 2, W // 12)
            spawn_warrior_count = 2 * warrior_pairs

            remaining_farmers_after_warrior = F - spawn_warrior_count
            remaining_wheat_after_warrior = W - 12 * warrior_pairs

            farm_pairs = min(remaining_farmers_after_warrior // 2, remaining_wheat_after_warrior // 10)
            spawn_farm_count = 2 * farm_pairs

            idx = 0
            for f in farmers:
                if idx < spawn_warrior_count:
                    environment.assign_group(f, "spawn warrior")
                elif idx < spawn_warrior_count + spawn_farm_count:
                    environment.assign_group(f, "spawn farmer")
                else:
                    environment.assign_group(f, "farm")
                idx += 1

        # All Warriors go to the Cave to attack
        for w in warriors:
            environment.assign_group(w, "cave")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the cave, Warriors should attack; Farmers return to village
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            elif role == "Farmer":
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "cave")
```