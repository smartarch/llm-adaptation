## Revised Strategy: Sustained Warrior Pressure with Continuous Spawning

**What was wrong before:** The previous version pulled warriors out at 1 HP and pulled all farmers back to the Village. It also capped spawns at two per type. Retreating removes damage from the fight, and the cap limited army growth. Since HP does not regenerate, a damaged warrior is still worth 3 damage per attack, so keeping it in the fight is better than sending it home. The Dragon also has only 50 HP, so the fight needs to be fast.

**Revised approach:**

- **Village:** All warriors go to the Cave every step. Spawning is no longer capped. Spawning a Warrior costs 12 wheat and needs two farmers in the spawn group. Farmers are not consumed by spawning, so the strategy computes how many spawns are affordable this step (`min(farmers // 2, wheat // 12)`) and assigns the matching number of farmer pairs to `spawn warrior`. Warriors are the damage dealers, so the army is grown with warriors. Remaining farmers go to `farm`, which keeps wheat income flowing.
- **Cave:** Every warrior attacks, regardless of HP. Warriors are never retreated, which maximizes the damage per step and shortens the fight.
- **Farmers never enter the Cave.** They only deal 1 damage and have 4 HP, so they would die quickly to the Dragon's area attack. They stay home to produce wheat and fund the warrior spawns.

**Assumptions:** The spawn cost is paid per spawn when a spawn is assigned, and the wheat budget is tracked within the step. Warriors that die are simply lost. If the Dragon's counterattacks wipe out all warriors, the spawn pipeline keeps producing new ones as long as farmers and wheat remain.

```py
import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Maximize sustained damage on the Dragon:
    - Every Warrior goes to the Cave and attacks every step (no retreating).
    - Farmers stay in the Village, farm wheat, and are used in pairs to spawn
      new Warriors as often as wheat allows.
    """

    WARRIOR_WHEAT_COST = 12

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat

        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        # All warriors head to the Cave to attack.
        for w in warriors:
            environment.assign_group(w, "cave")

        # Number of Warrior spawns affordable this step:
        # each spawn needs a pair of farmers and 12 wheat.
        max_by_farmers = len(farmers) // 2
        max_by_wheat = wheat // self.WARRIOR_WHEAT_COST
        num_spawns = min(max_by_farmers, max_by_wheat)

        spawn_count = 2 * num_spawns
        for f in farmers[:spawn_count]:
            environment.assign_group(f, "spawn warrior")
        for f in farmers[spawn_count:]:
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.role == "Warrior":
                # Keep attacking regardless of HP: damage now shortens the fight.
                environment.assign_group(c, "attack")
            else:
                # Farmers are too fragile for the Cave; send them home.
                environment.assign_group(c, "village")
```