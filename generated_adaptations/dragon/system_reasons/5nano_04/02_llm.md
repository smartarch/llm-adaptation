Reasoning and adaptation strategy

Goal-driven strategy
- Move all Warriors to the Cave and then have them attack the Dragon as soon as possible. This ensures the Dragon is assaulted early (fulfills the requirement to attack within the first 15 steps) and concentrates damage output where it matters.
- Keep Farmers in the Village to work on the farm and to provide wheat for spawning new villagers. Farmers are the source of wheat; without wheat we cannot spawn new villagers.
- Use the two spawn groups in the Village to generate more Farmers and Warriors:
  - spawn farmer: for every two villagers assigned here and at least 10 wheat in the Farm, a new Farmer is spawned.
  - spawn warrior: for every two villagers assigned here and at least 12 wheat in the Farm, a new Warrior is spawned.
  This lets us grow both sides of the army to increase DPS on the Dragon over time.
- Ensure spawn actions are conditional on available resources:
  - If there are at least two Farmers and wheat >= 10, assign two Farmers to spawn farmer.
  - If after that there are two more Farmers and wheat >= 12, assign two Farmers to spawn warrior.
  Remaining Farmers stay in the Village to farm or wait for future spawns.
- In Cave step, re-affirm the Warrior plan: all Warriors attack the Dragon, Farmers go back to Village (to continue farming or to participate in future spawns). This aligns with the requirement that all Warriors should attack after moving to the Cave, and Farmers should stay in the Village.

Implementation notes
- The code uses environment.assign_group(component, group_id) to assign each villager to exactly one group.
- All Warriors are assigned to Cave during the Village phase, and then to Attack during the Cave phase to ensure they fight the Dragon after arriving in the Cave.
- Spawn groups are used only in the Village phase and depend on current wheat in environment.farm.wheat.
- The strategy aims to spawn a few new Farmers and Warriors early, while ensuring we maintain enough Warriors in the Cave for timely Dragon DPS.

Code (Python)

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._spawn_state = {}

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Groups:
        # - "farm": stay in Village and farm
        # - "cave": go to the Cave
        # - "spawn farmer": spawn new Farmer (needs 2 villagers + 10 wheat)
        # - "spawn warrior": spawn new Warrior (needs 2 villagers + 12 wheat)

        # Gather villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Default: all farmers stay in farm
        for f in farmers:
            environment.assign_group(f, "farm")

        # Wheat available on the Farm
        wheat = getattr(getattr(environment, "farm", None), "wheat", 0)

        # Determine farmers to assign to spawn groups
        to_spawn_farmers = []
        if len(farmers) >= 2 and wheat >= 10:
            to_spawn_farmers = farmers[:2]
            for c in to_spawn_farmers:
                environment.assign_group(c, "spawn farmer")

        # Remaining farmers after selecting spawn farmers
        remaining_after_farm_spawn = [f for f in farmers if f not in to_spawn_farmers]

        to_spawn_warriors = []
        if len(remaining_after_farm_spawn) >= 2 and wheat >= 12:
            to_spawn_warriors = remaining_after_farm_spawn[:2]
            for c in to_spawn_warriors:
                environment.assign_group(c, "spawn warrior")

        # Any farmers not involved in spawning stay farming
        # (They were already assigned to "farm" above; nothing else to do)

        # Move all Warriors toward the Cave (preparation for attack next step)
        for w in warriors:
            environment.assign_group(w, "cave")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In Cave:
        # - Warriors attack the Dragon
        # - Farmers go back to Village (stay in Village)
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```