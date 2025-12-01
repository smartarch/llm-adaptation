Reasoning and updated strategy:
- Problem with previous approach: Spawning and warrior deployment were not balanced. Too many villagers could be sent to the cave too early or not enough wheat was accrued to sustain spawning. The dragon’s counterattack can wipe out villagers in cave, so we should be cautious with how many villagers we send there at once.
- Key goals to improve win rate and speed:
  - Prioritize wheat production in the Village with Farmers to build a robust wheat reservoir.
  - Spawn new Farmers first (uses 10 wheat and 2 villagers) to accelerate long-term wheat production.
  - Only spawn Warriors after we have a healthy pool of Farmers and sufficient wheat, to steadily increase DPS without starving wheat for future spawns.
  - Keep all Warriors in the Cave attacking the Dragon, and send Farmers back to Village to continue farming or spawning.
  - In the Cave, limit risk by not overloading with Warriors; however, the strategy must still respect “All Warriors should go to the Cave.”
- Concrete plan:
  - In assign_in_village:
    - Gather Farmers and Warriors. Spawn as many Farmers as possible using the 10 wheat per two Farmers (spawn farmer). Consume wheat accordingly (computed based on current wheat).
    - With the remaining Farmers, spawn as many Warriors as possible using 12 wheat per two villagers (spawn warrior). Consume wheat accordingly (computed from wheat remaining after Farmer spawns).
    - Assign all spawned Farmers or remaining Farmers to either spawn farmer or farm groups as appropriate; assign all Warriors to the cave (to meet the rule that Warriors should attack the Dragon).
  - In assign_in_cave:
    - Assign all Warriors to the attack group.
    - Assign Farmers to the village group so they can continue farming or spawning.

This approach aims to grow wheat quickly, then steadily increase DPS while avoiding excessive risk in the cave, which should help reduce the number of turns to kill the Dragon.

Code (Python):

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        In the Village:
        - Spawn farmers as much as possible given 10 wheat per spawn (2 farmers per spawn).
        - With remaining farmers, spawn warriors if there is enough wheat (12 wheat per spawn, 2 villagers per spawn).
        - Remaining farmers go to the 'farm' group.
        - All Warriors go to the Cave (attack).
        """
        # Separate villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        wheat = int(getattr(environment.farm, "wheat", 0))

        # 1) Spawn farmers as much as possible
        max_farm_spawns = min(len(farmers) // 2, wheat // 10)
        spawn_farmers = farmers[:2 * max_farm_spawns]
        remaining_farmers = farmers[2 * max_farm_spawns:]

        # Wheat after farming spawns
        wheat_after_farm = wheat - max_farm_spawns * 10

        # 2) Spawn warriors if possible with remaining farmers and wheat
        spawn_warriors = []
        max_war_spawns = min(len(remaining_farmers) // 2, wheat_after_farm // 12)
        spawn_warriors = remaining_farmers[:2 * max_war_spawns]
        remaining_farmers = remaining_farmers[2 * max_war_spawns:]

        # 3) Assign groups
        for c in spawn_farmers:
            environment.assign_group(c, "spawn farmer")
        for c in remaining_farmers:
            environment.assign_group(c, "farm")
        for c in spawn_warriors:
            environment.assign_group(c, "spawn warrior")

        # All existing Warriors go to the Cave
        for c in warriors:
            environment.assign_group(c, "cave")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        In the Cave:
        - Warriors attack the Dragon.
        - Farmers go back to the Village.
        """
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```