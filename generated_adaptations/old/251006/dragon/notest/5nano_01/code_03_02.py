"""
Reasoning about the adaptation strategy (embedded as comments for the code narrative):
- Problem observed: previous strategy spawned many villagers and allowed the dragon to inflict damage largely on the cave population,
  leading to very poor win rates. There is a risk when there are many farmers in the cave, since the dragon can attack them with
  AOE-like effects and random targeting.
- Core constraints:
  - All Warriors must go to the Cave to attack the Dragon.
  - All Farmers must stay in the Village to farm and, if possible, spawn more villagers.
  - Spawning rules exist, but aggressive spawning led to too many villagers being exposed to dragon attacks.
- Revised strategy (simple and safer):
  - In assign_in_village:
    - Do not use any spawn groups. This prevents creating large villages that can be wiped out by dragon attacks.
    - Move all Warriors to the cave (attack) and keep all Farmers in the Village (farm).
  - In assign_in_cave:
    - All Warriors to attack the Dragon.
    - All Farmers to go back to the Village (to continue farming or supply future planning).
- Rationale:
  - Minimizes the number of villagers exposed to dragon retaliation (stays in cave minimal to avoid AOE).
  - Ensures a stable farming population to accumulate wheat for long-term capability, without risking large chain spawns.
  - Keeps to the explicit requirement that all Warriors attack the Dragon and Farmers remain in the Village as much as possible.
- This approach avoids mid-step multi-assignment issues by using a single deterministic assignment per component per method call, complying with the unit test expectations.

"""
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Strategy:
        - Warriors -> cave (attack)
        - Farmers -> farm (stay in Village)
        - No spawning actions to avoid increasing exposure and test instability.
        """
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "cave")
            else:
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Strategy:
        - Warriors -> attack (to maximize damage to Dragon)
        - Farmers -> village (to return to farming)
        """
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")