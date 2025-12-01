Reasoning and improved strategy

Goal-focused improvements:
- Prioritize early DPS: spawn Warriors as early as possible because each Warrior contributes 3 damage per turn, accelerating dragon kill.
- Use Farmers to fuel spawns efficiently: Farmers are the only source of new villagers via spawns. We should allocate farmers to spawn Warriors first (when wheat allows), then to spawn Farmers if wheat remains, and only after that to farming to grow wheat for future spawns.
- Maintain the rule that all Warriors go to the Cave and attack the Dragon, while Farmers stay in the Village to farm or spawn.
- Do spawning decisions in a deterministic, wheat-aware way each step to maximize growth rate early in the game.

Adaptation strategy
In assign_in_village:
- Compute how many Warrior spawns we can trigger this step:
  - warrior_spawns = min(number_of_farmers // 2, wheat // 12)
- After allocating Warrior spawns, compute how many Farmer spawns we can trigger with the remaining Farmers and Wheat:
  - farmer_spawns = min((number_of_farmers - 2 * warrior_spawns) // 2, (wheat - 12 * warrior_spawns) // 10)
- Assign components in input order:
  - Warriors always go to "cave" (to attack).
  - Farmers: first assign to "spawn warrior" for 2 farmers per pair (up to 2 * warrior_spawns), then to "spawn farmer" for the next 2 farmers per pair (up to 2 * farmer_spawns), and finally the rest to "farm".

In assign_in_cave:
- Warriors assign to "attack" (to hit the Dragon).
- Farmers assign to "village" (to return to farming/spawning).

This approach aggressively builds up Warrior count early while still growing Wheat production to enable future spawns, improving the chance to defeat the Dragon within the 30-step limit.

Python code

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Divide villagers in the Village into:
        - farm: stay in Village and farm
        - cave: go to the Cave (for Warriors to attack later)
        - spawn farmer: for every two villagers in this group and 10 wheat, a new Farmer is spawned
        - spawn warrior: for every two villagers in this group and 12 wheat, a new Warrior is spawned
        Strategy:
        - Spawn Warriors first (to maximize early DPS), using 2 farmers per Warrior spawn and 12 wheat per pair.
        - Then spawn Farmers with any remaining Wheat/Farmers.
        - Remaining Farmers go to farming.
        """
        # Classify current farmers and warriors
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        n_farmers = len(farmers)

        # Wheat available for spawning
        wheat = 0
        try:
            wheat = environment.farm.wheat
        except Exception:
            wheat = 0

        # Phase 1: determine how many Warrior spawns we can trigger this step
        warrior_spawns = min(n_farmers // 2, wheat // 12)
        # Remaining farmers after Warrior spawns
        remaining_farmers_after_warriors = n_farmers - 2 * warrior_spawns
        wheat_after_warriors = max(0, wheat - 12 * warrior_spawns)

        # Phase 2: determine how many Farmer spawns we can trigger with remaining resources
        farmer_spawns = min(remaining_farmers_after_warriors // 2, wheat_after_warriors // 10)
        # Sizes for quick checks (2 per spawn)
        warrior_spawn_size = 2 * warrior_spawns
        farmer_spawn_size = 2 * farmer_spawns

        # Assign in input order
        farmer_index = 0
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                # All Warriors go to the Cave
                environment.assign_group(c, "cave")
            else:
                # Farmers: allocate to spawn warrior first, then spawn farmer, then farm
                if farmer_index < warrior_spawn_size:
                    environment.assign_group(c, "spawn warrior")
                elif farmer_index < warrior_spawn_size + farmer_spawn_size:
                    environment.assign_group(c, "spawn farmer")
                else:
                    environment.assign_group(c, "farm")
                farmer_index += 1

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        In the Cave:
        - attack: Warriors attack the Dragon
        - cave: Stay in the Cave
        - village: Go to the Village
        """
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```