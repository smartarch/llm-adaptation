Strategy reasoning and plan

Goal-driven reasoning:
- You want to win quickly by maximizing early Dragon damage while ensuring the Dragon is attacked within the first 15 steps.
- Warriors are the primary damage dealers, but they must start in the Cave to attack. Farmers mainly stay in the Village to farm and to help spawn more villagers.
- Spawning strategy: use "spawn farmer" and "spawn warrior" groups to generate new villagers. Each spawn group requires at least two villagers assigned to that group and a wheat cost (10 for Farmers, 12 for Warriors). We should leverage farm wheat to trigger spawns, ensuring both new Farmers and new Warriors appear.
- To satisfy constraints, we will:
  - In village: move all existing Warriors to the Cave (so they move toward attacking the Dragon). Place Farmers into some combination of:
    - farm (stay in Village and farm)
    - spawn farmer (to trigger farmer spawns)
    - spawn warrior (to trigger warrior spawns)
  - We will softly balance the numbers to ensure both some new Farmers and some new Warriors can spawn, while keeping enough Farmers to continue farming.
  - In cave: send all Warriors to attack the Dragon (group "attack") and send Farmers back to the Village (group "village") to satisfy “All farmers should stay in the Village.”
  - Ensure at least one Dragon attack occurs by ensuring at least one Warrior is in the attack group in the cave early. With existing Warriors plus spawned Warriors, this should hold within the first 15 steps.
  - Keep “attack” concentrated: most Warriors should be in the cave attacking the Dragon when possible (we assign all current Warriors to attack in the cave step).

Implementation plan:
- assign_in_village
  - Gather lists of Farmers and Warriors from components.
  - Move all Warriors to the cave (environment.assign_group(component, "cave")).
  - For Farmers, decide counts for three groups: farm, spawn farmer, spawn warrior.
  - Use environment.farm.wheat as a lightweight heuristic to decide spawning:
    - If wheat is high (e.g., >= 24) and there are enough Farmers, assign some to spawn farmers and possibly spawn warriors.
    - If wheat is moderate (>= 12) and there are enough Farmers, spawn at least some warriors.
    - Otherwise, keep most Farmers in farm or a small number in spawn options if wheat suffices.
  - Always ensure every Farmer is assigned to exactly one of: "farm", "spawn farmer", or "spawn warrior".
- assign_in_cave
  - Move all Warriors to "attack".
  - Move all Farmers to "village" to stay in the Village (as required).

This strategy guarantees:
- All Warriors eventually attack (in cave), with a bias toward attacking the Dragon as early as possible.
- Farmers remain in the Village most of the time, while a deliberate subset participates in spawning to grow the force.
- The Dragon is attacked in the first 15 steps due to initial Warriors and spawned Warriors moving toward attack.

Code (Python)

```py
import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Split villagers into Farmers and Warriors
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # 1) All existing Warriors should go to the Cave
        for w in warriors:
            environment.assign_group(w, "cave")

        # 2) Distribute Farmers among farm / spawn farmer / spawn warrior
        total_farmers = len(farmers)

        spawn_farmer_count = 0
        spawn_warrior_count = 0
        farm_count = total_farmers  # default all to farming, may be reduced

        # Wheat available (read-only in this environment)
        wheat = getattr(getattr(environment, "farm", None), "wheat", 0)

        # Heuristic spawning plan to meet "a few" spawns
        if total_farmers >= 6 and wheat >= 24:
            # Aim for some farmer spawns and some warrior spawns
            spawn_farmer_count = min( max(2, total_farmers // 3), total_farmers - 2 )
            remaining = total_farmers - spawn_farmer_count
            # Try to spawn some warriors from the remaining pool if wheat allows
            if wheat >= 36 and remaining >= 2:
                spawn_warrior_count = min( max(1, remaining // 3), remaining - 1 )
            farm_count = total_farmers - spawn_farmer_count - spawn_warrior_count
        elif wheat >= 12 and total_farmers >= 4:
            # Moderate spawning: focus on warrior spawns if possible
            spawn_warrior_count = min(2, total_farmers - 2)
            farm_count = total_farmers - spawn_warrior_count

        # Assign Farmers to their groups
        idx = 0
        # spawn farmer
        for _ in range(spawn_farmer_count):
            if idx < total_farmers:
                environment.assign_group(farmers[idx], "spawn farmer")
                idx += 1
        # spawn warrior
        for _ in range(spawn_warrior_count):
            if idx < total_farmers:
                environment.assign_group(farmers[idx], "spawn warrior")
                idx += 1
        # keep remaining as farmers who farm
        for _ in range(farm_count):
            if idx < total_farmers:
                environment.assign_group(farmers[idx], "farm")
                idx += 1

        # If there are farmers left unassigned due to mismatch, assign them to farm by default
        while idx < total_farmers:
            environment.assign_group(farmers[idx], "farm")
            idx += 1

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave, send Warriors to attack, Farmers return to Village
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                # Farmers should stay in the Village
                environment.assign_group(c, "village")
```