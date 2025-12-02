Reasoning and improved strategy

Goal alignment
- All Warriors should go to the Cave and attack the Dragon as soon as possible.
- All Farmers stay in the Village to farm and provide population growth via spawning.
- Spawn events are driven by pairs of villagers and wheat. Spawning more villagers earlier increases DPS against the Dragon and accelerates victory.
- We want the Dragon attacked early (within the first 15 steps) and keep a strong presence of Warriors in the Cave to maximize damage.

Key improvements over the previous approach
- Aggressive but safe spawning: Instead of deciding spawn groups in isolation, we compute the maximum number of spawn events we can support this step given the current wheat and available farmers. We spawn as many Farmers and Warriors as allowed by wheat and farmer availability, using 2 farmers per spawn event for each type (farm and warrior). This accelerates population growth while respecting resource constraints.
- Consistent resource accounting: We account for wheat consumption when planning both spawn farmer and spawn warrior groups in the same step, so we don’t over-commit beyond available wheat.
- Clear warrior strategy: All Warriors are moved to attack immediately and stay in the Cave to maximize DPS from step 1 onward.
- Farmers primarily farm or spawn, with no wandering that would delay farming or spawning opportunities.

Strategy outline
- assign_in_village:
  - Move all Warriors to the Cave (group "cave") so they can attack later.
  - Use Farmers in the Village to spawn new villagers if wheat allows:
    - Compute max possible spawn events for Farmers: max_spawn_farmers = min(number_of_available_farmers // 2, wheat // 10)
    - Execute as many spawn-farmer events as possible (assign 2*count farmers to "spawn farmer" group).
    - Deduct consumed wheat (10 per event) from wheat.
    - With remaining farmers and remaining wheat, compute max possible spawn events for Warriors: max_spawn_warriors = min( remaining_farmers // 2, remaining_wheat // 12 )
    - Execute as many spawn-warrior events as possible (assign 2*count farmers to "spawn warrior" group).
    - Deduct consumed wheat (12 per event) from wheat.
    - The rest of Farmers stay in the Village (group "farm").
  - Assign all Warriors to the "cave" group for later attacking.

- assign_in_cave:
  - Move all Warriors to the "attack" group (in the Cave).
  - Move all Farmers to the "village" group (back to the Village).

Code (Python)

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Assign villagers in the Village into:
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

        # Determine spawns: maximize spawns given resources and farmer availability
        # Spawn farmers: each event uses 2 farmers and 10 wheat
        max_spawn_farmers = min(len(available_farmers) // 2, wheat // 10)
        if max_spawn_farmers > 0:
            take = 2 * max_spawn_farmers
            to_spawn_farmer = available_farmers[:take]
            available_farmers = available_farmers[take:]
            wheat -= max_spawn_farmers * 10  # consume wheat for spawned farmers
        else:
            to_spawn_farmer = []

        # Spawn warriors: with remaining farmers and wheat, each event uses 2 farmers and 12 wheat
        max_spawn_warriors = min(len(available_farmers) // 2, wheat // 12)
        if max_spawn_warriors > 0:
            take = 2 * max_spawn_warriors
            to_spawn_warrior = available_farmers[:take]
            available_farmers = available_farmers[take:]
            wheat -= max_spawn_warriors * 12  # consume wheat for spawned warriors
        else:
            to_spawn_warrior = []

        # Remaining farmers go to farming in the Village
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
        Assign villagers in the Cave into:
        - attack: Attack the Dragon
        - cave: Stay in the Cave
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