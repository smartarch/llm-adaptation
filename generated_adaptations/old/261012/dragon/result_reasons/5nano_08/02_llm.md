Strategy reasoning and plan

Goal-driven adaptation:
- Warriors must all go to the Cave and attack the Dragon as soon as possible. Therefore, in the village phase, assign every Warrior to the “cave” group (so they travel to the Cave and can fight once in the cave phase).
- Farmers must stay in the Village. However, Farmers are our source of both wheat and potential new villagers. We should let Farmers farm, and occasionally use some Farmers to spawn new villagers (both Farmers and Warriors) when resource (wheat) allows.
- Spawning strategy:
  - The spawning mechanism uses two villagers assigned to a spawn group plus a wheat cost to create a new Villager of the corresponding type.
  - To spawn at least a few new villagers, allocate small, deterministic batches only when wheat is available.
  - Spawn Farmer: requires two villagers in the “spawn farmer” group and 10 wheat.
  - Spawn Warrior: requires two villagers in the “spawn warrior” group and 12 wheat.
  - When possible, spawn both a new Farmer and a new Warrior in the same village phase by selecting four Farmers (two for each spawn group) if wheat allows (roughly 22 wheat total: 10 for farmer spawn and 12 for warrior spawn). This increases DPS and helps ensure Dragon death within 30 steps.
- Cave phase behavior:
  - All Warriors in the cave should be in the “attack” group to fight the Dragon. Farmers in the cave should go back to the Village (to continue farming and spawning).
- Step behavior:
  - The first 15 steps are the critical window to ensure the Dragon is attacked; by proactively moving Warriors to the Cave early and spawning additional combatants when wheat allows, we raise the odds of a Dragon kill within 15 steps.

Implementation notes:
- All components must be assigned exactly once per step.
- The provided environment API is used to issue group assignments: environment.assign_group(component, group_id).
- The adaptation follows your required groups:
  - Village step: farm, cave, spawn farmer, spawn warrior
  - Cave step: attack, cave, village
- The actual spawning is governed by the game engine using the two-villager + wheat rule; our strategy merely selects the appropriate villagers to the spawn groups when feasible.

Code (Python)

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Assign villagers in the Village to:
        - "farm": stay in village and farm
        - "cave": go to the Cave (for Warriors only, per strategy)
        - "spawn farmer": for every two villagers in this group and 10 wheat, a new Farmer is spawned
        - "spawn warrior": for every two villagers in this group and 12 wheat, a new Warrior is spawned
        """
        # Collect villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Current wheat in the Farm
        wheat = getattr(getattr(environment, "farm", None), "wheat", 0)

        # We will build a map: component -> target_group
        assignments = {}

        # Default: farmers stay in village and farm
        for f in farmers:
            assignments[f] = "farm"

        # Move all Warriors to the Cave (they will attack from the cave)
        for w in warriors:
            assignments[w] = "cave"

        # Decide on spawning farmers/warriors (use wheat when possible)
        # Try to spawn both a farmer and a warrior if we have enough farmers and enough wheat.
        to_spawn_farmer = []
        to_spawn_warrior = []

        if len(farmers) >= 4 and wheat >= 22:
            # Use four farmers: two for each spawn type
            to_spawn_farmer = farmers[:2]
            to_spawn_warrior = farmers[2:4]
        else:
            # Try to spawn at least one farmer if possible
            if len(farmers) >= 2 and wheat >= 10:
                to_spawn_farmer = farmers[:2]
            # Try to spawn at least one warrior if possible (don't reuse the same two)
            if len(farmers) >= 4 and wheat >= 12:
                to_spawn_warrior = farmers[2:4]

        for f in to_spawn_farmer:
            assignments[f] = "spawn farmer"
        for f in to_spawn_warrior:
            if f not in to_spawn_farmer:
                assignments[f] = "spawn warrior"

        # Apply assignments to environment (one assignment per villager)
        for c, g in assignments.items():
            environment.assign_group(c, g)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Assign villagers in the Cave to:
        - "attack": Attack the Dragon (all Warriors)
        - "cave": Stay in the Cave (if any non-Warriors end up here)
        - "village": Go to the Village (Farmers return to farm)
        """
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```