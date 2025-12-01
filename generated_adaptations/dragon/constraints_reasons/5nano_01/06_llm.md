Reasoning and updated strategy

Root cause
- The previous adaptation sometimes failed to spawn any new Warriors in scenarios where wheat was available but the spawning order or allocation didn’t guarantee warrior spawns. The test suite requires at least a few new Warriors to be spawned to increase kill chances.

Updated strategy
- In village assignments:
  - Allocate Warriors to the Cave so they can attack the Dragon.
  - Use Farmers as potential spawners:
    - First allocate 2-Farmer groups to “spawn warrior” (needs 12 wheat) to ensure Warrior spawns whenever possible.
    - Then allocate 2-Farmer groups to “spawn farmer” (needs 10 wheat) to maintain a growing farm and workforce.
    - Any remaining Farmers stay in the Village to farm (group "farm").
  - Spawning decisions are made based on available wheat and number of Farmers:
    - s_war = min(n_farmers // 2, wheat // 12)
    - wheat after spawning wars: wheat - 12*s_war
    - s_farm = min((n_farmers - 2*s_war) // 2, (wheat_after_war) // 10)
- In cave assignments:
  - All Warriors are assigned to the “attack” group (they will attack the Dragon).
  - All Farmers return to the Village (group "village"), ensuring Farmers stay in the Village when not spawning.
- This approach guarantees:
  - Warriors are spawned whenever possible (given wheat and sufficient farmers).
  - A mix of new farmers and warriors is created, meeting both spawning requirements and the need for more fighters.

Code

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Divide Village villagers into:
        - farm: stay in Village and farm
        - cave: go to the Cave (to join attack later)
        - spawn farmer: for every two villagers assigned and 10 wheat, spawn a new Farmer
        - spawn warrior: for every two villagers assigned and 12 wheat, spawn a new Warrior
        """
        # Separate current villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        n_farmers = len(farmers)
        n_warriors = len(warriors)

        # Wheat available for spawning (from the Farm)
        wheat = 0
        farm = getattr(environment, "farm", None)
        if farm is not None:
            w_attr = getattr(farm, "wheat", None)
            if w_attr is not None:
                try:
                    wheat = int(w_attr)
                except (TypeError, ValueError):
                    wheat = 0

        # Spawning plan:
        # First spawn warriors (needs 2 farmers and 12 wheat per warrior)
        s_war = min(n_farmers // 2, max(0, wheat // 12))
        wheat_after_war = wheat - (12 * s_war)

        # Then spawn farmers (needs 2 farmers and 10 wheat per farmer)
        s_farm = min((n_farmers - 2 * s_war) // 2, max(0, wheat_after_war // 10))

        idx = 0
        # Assign first 2*s_war farmers to "spawn warrior"
        for _ in range(2 * s_war):
            environment.assign_group(farmers[idx], "spawn warrior")
            idx += 1

        # Assign next 2*s_farm farmers to "spawn farmer"
        for _ in range(2 * s_farm):
            environment.assign_group(farmers[idx], "spawn farmer")
            idx += 1

        # Remaining farmers -> "farm" (stay in Village and farm)
        for i in range(idx, n_farmers):
            environment.assign_group(farmers[i], "farm")

        # All Warriors should go to the Cave (to join the attack)
        for w in warriors:
            environment.assign_group(w, "cave")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Divide Cave villagers into:
        - attack: Warriors attack the Dragon
        - cave: stay in cave (unused for Warriors in this strategy)
        - village: Farmers go back to Village
        """
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```