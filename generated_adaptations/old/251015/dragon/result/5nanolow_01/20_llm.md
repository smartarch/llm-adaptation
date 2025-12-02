Reasoning and new adaptation strategy:
- Objective remains to kill the Dragon as fast as possible within 30 steps, under constraints: Warriors must be in the Cave to attack, Farmers stay in the Village to farm and spawn.
- Observations:
  - Warriors provide the bulk of DPS when in the Cave; keep them there at all times.
  - Wheat is the resource that enables spawning; farming in the Village should continuously generate wheat to enable more spawns over time.
  - Spawning a new villager increases future DPS, but costs turns. A simple, aggressive yet bounded policy can improve turns-to-win by ensuring we always use available wheat to spawn as soon as possible, while not delaying Warriors’ DPS.
- New targeted policy:
  - In assign_in_village:
    - Move all Warriors to the Cave (attack).
    - Always try to spawn as many Farmers as possible this turn, using the rule: spawn_f_count = min(num_farmers // 2, wheat // 10). Assign 2 * spawn_f_count Farmers to "spawn farmer". The rest of Farmers go to "farm".
    - Do not spawn Warriors here (to avoid consuming wheat that could be used for farmer spawns, and because Warriors are already in the Cave attacking).
  - In assign_in_cave:
    - Move all Warriors to "attack".
    - Move all Farmers in the Cave to "village".
- This approach makes spawning a consistent, data-driven action every turn (when possible) and keeps Warriors always maximizing DPS, which should reduce the number of turns to kill the Dragon.

Python code (class implementation):

```py
import abc

# Assuming the base class can be imported from the given module path
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Aggressive, bounded, data-driven spawning strategy:
        - Warriors -> cave (attack)
        - Farmers -> village (farm/spawn)
        - Spawn as many Farmers as possible this turn:
            spawn_f_count = min(num_farmers // 2, wheat // 10)
            Assign 2 * spawn_f_count farmers to "spawn farmer"
            Remaining farmers to "farm"
        - No Warrior-spawns in village; Warriors are already in cave.
        """
        # Separate by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # 1) Always send Warriors to Cave to attack
        for w in warriors:
            environment.assign_group(w, "cave")

        # 2) Spawning decisions in Village (Farmers only)
        wheat = getattr(environment.farm, "wheat", 0)
        num_farmers = len(farmers)

        # Potential farmer spawns (needs 2 farmers + 10 wheat each)
        spawn_f_count = min(num_farmers // 2, wheat // 10)

        # Wheat left after farmer spawns
        wheat_after_farm = wheat - 10 * spawn_f_count

        # Assign spawning groups
        spawn_farmer_candidates = farmers[: 2 * spawn_f_count]
        remaining_farmers = farmers[2 * spawn_f_count:]

        for f in spawn_farmer_candidates:
            environment.assign_group(f, "spawn farmer")

        # Remaining farmers go to farming
        for f in remaining_farmers:
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        In the Cave, keep Warriors in "attack" and move Farmers back to the Village.
        """
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            elif role == "Farmer":
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "cave")
```