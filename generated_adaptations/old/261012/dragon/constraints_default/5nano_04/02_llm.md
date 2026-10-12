Reasoning and strategy description:
- Overall goal: kill the Dragon as fast as possible within 30 steps, while managing wheat for spawning new villagers.
- Key observations:
  - Warriors are the primary damage dealers (3 damage when attacking), so they should quickly reach the Cave to attack the Dragon.
  - Farmers generate wheat when farming (5 wheat per Farmer per farming action). Wheat is needed to spawn new villagers.
  - Spawning is governed by two rules:
    - Spawn Farmer: for every two villagers assigned to the "spawn farmer" group and 10 wheat, one new Farmer is spawned.
    - Spawn Warrior: for every two villagers assigned to the "spawn warrior" group and 12 wheat, one new Warrior is spawned.
  - To maximize DPS growth, we should:
    - Move all Warriors to the Cave (to go towards the Dragon).
    - Keep Farmers in the Village, farming to accumulate wheat.
    - Use farming villagers to spawn additional villagers when enough wheat is available.
    - Prefer spawning Farmers first when there is sufficient wheat, since spawning more Farmers increases wheat production in the long run, enabling more spawns and more combatants over time.
    - If wheat remains and there are more farmers, spawn Warriors to increase DPS, but ensure all Warriors are in the Cave for combat.
- Implementation strategy (in two phases per step):
  - assign_in_village:
    - Move all Warriors to the Cave (group "cave").
    - For Farmers, greedily spawn using available wheat:
      - First, pair up Farmers to the "spawn farmer" group while wheat >= 10.
      - Then, if there are still unpaired Farmers and wheat >= 12, pair up for "spawn warrior" to create additional attackers.
      - Any remaining Farmers go to the "farm" group to continue wheat production.
  - assign_in_cave:
    - In the Cave, assign Warriors to "attack" (Dragon) and Farmers to "village" (go back to the Village to keep farming/spawning).
- This strategy keeps Warriors advancing toward the Dragon while gradually growing the population and wheat stock in the Village, balancing immediate DPS with long-term population growth to meet the 30-step win condition.

Python code (class SmartAdaptation implementing the strategy):

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate villagers by role
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # 1) All Warriors should go to the Cave
        for c in warriors:
            environment.assign_group(c, "cave")

        # 2) Spawn logic for Farmers (in the Village)
        if farmers:
            # Work with a copy for processing
            unassigned = farmers[:]
            wheat = environment.farm.wheat
            i = 0

            # Spawn Farmers in pairs if enough wheat (10)
            while i + 1 < len(unassigned) and wheat >= 10:
                environment.assign_group(unassigned[i], "spawn farmer")
                environment.assign_group(unassigned[i + 1], "spawn farmer")
                i += 2
                wheat -= 10

            # If still possible, spawn Warriors in pairs if enough wheat (12)
            while i + 1 < len(unassigned) and wheat >= 12:
                environment.assign_group(unassigned[i], "spawn warrior")
                environment.assign_group(unassigned[i + 1], "spawn warrior")
                i += 2
                wheat -= 12

            # Remaining farmers go farming
            for j in range(i, len(unassigned)):
                environment.assign_group(unassigned[j], "farm")

        # Done with village assignments
        return

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave: Warriors attack the Dragon; Farmers return to Village
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```