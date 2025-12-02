Reasoning and improved strategy

Goal and constraints recap
- All Warriors must go to the Cave and attack the Dragon as soon as possible.
- All Farmers stay in the Village to farm (and enable spawning) rather than wandering.
- Spawning uses two villagers assigned to a spawn group plus wheat:
  - spawn farmer consumes 10 wheat to create 1 new Farmer (needs 2 farmers in the group)
  - spawn warrior consumes 12 wheat to create 1 new Warrior (needs 2 farmers in the group)
- We want to attack early (within the first 15 steps) and have a healthy number of Warriors in the Cave most of the time.

Key improvements over the previous approach
- Aggressive, globally optimal in-step spawning: Instead of greedily taking two farmers for one spawn type and then another two for the other type, compute the maximum number of spawn events for both farmer and warrior in the current step given the actual wheat and available farmers. This maximizes the total number of new villagers generated this step, increasing DPS earlier.
- Deterministic resource accounting: We explicitly allocate wheat to spawn farmer events first, then to spawn warrior events with the remaining wheat, ensuring we never overspend wheat in a single step.
- Early attack assurance: All Warriors are moved to the Cave to attack as soon as possible, and spawning is performed to increase future Warrior numbers without delaying the attack.

Strategy outline
- assign_in_village:
  - Move all Warriors to the Cave (group "cave").
  - From Farmers in the Village, compute the maximum feasible spawn events for farmers (Kf) and warriors (Kw) this step:
    - Kf = min(number_of_farmers // 2, wheat // 10)
    - After removing 2*Kf farmers and 10*Kf wheat, Kw = min(remaining_farmers // 2, remaining_wheat // 12)
  - Assign 2*Kf farmers to "spawn farmer", 2*Kw farmers to "spawn warrior", and the rest to "farm".
  - This maximizes early population growth and keeps Warriors ready in the Cave.
- assign_in_cave:
  - All Warriors go to "attack"; Farmers go to "village".

Python code (one code block)

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Divides villagers in the Village into:
        - farm: Farmers stay in the Village to farm
        - cave: Warriors go to the Cave
        - spawn farmer: For every two villagers assigned to this group and 10 wheat, a new Farmer is spawned.
        - spawn warrior: For every two villagers assigned to this group and 12 wheat, a new Warrior is spawned.
        """
        # Separate by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Default allocations
        to_farm = []
        to_cave = []
        to_spawn_farmer = []
        to_spawn_warrior = []

        # All Warriors should head to the Cave to attack
        to_cave.extend(warriors)

        # Farmers present in village
        available_farmers = list(farmers)

        # Wheat available in the Farm
        wheat = 0
        farm_env = getattr(environment, "farm", None)
        if farm_env is not None:
            wheat = getattr(farm_env, "wheat", 0)

        # Compute maximum spawn events this step given resources
        # Spawn farmers first
        max_spawn_farmers = min(len(available_farmers) // 2, wheat // 10)
        if max_spawn_farmers > 0:
            take = 2 * max_spawn_farmers
            to_spawn_farmer = available_farmers[:take]
            available_farmers = available_farmers[take:]
            wheat -= max_spawn_farmers * 10  # consume wheat for spawned farmers

        # With remaining resources, spawn warriors
        max_spawn_warriors = min(len(available_farmers) // 2, wheat // 12)
        if max_spawn_warriors > 0:
            take = 2 * max_spawn_warriors
            to_spawn_warrior = available_farmers[:take]
            available_farmers = available_farmers[take:]
            wheat -= max_spawn_warriors * 12  # consume wheat for spawned warriors

        # Remaining farmers stay in the Village to farm
        to_farm = available_farmers

        # Assign groups
        for c in to_farm:
            environment.assign_group(c, "farm")
        for c in to_spawn_farmer:
            environment.assign_group(c, "spawn farmer")
        for c in to_spawn_warrior:
            environment.assign_group(c, "spawn warrior")
        for c in to_cave:
            environment.assign_group(c, "cave")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Divides villagers in the Cave into:
        - attack: Attack the Dragon
        - cave: Stay in the Cave (not used in this strategy, but kept for completeness)
        - village: Go to the Village
        """
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                # Farmers go back to the Village
                environment.assign_group(c, "village")
```