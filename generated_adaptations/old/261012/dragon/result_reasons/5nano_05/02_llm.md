Reasoning and adaptation strategy

Analysis of the problem and constraints:
- Warriors must be moved to the Cave and then attack the Dragon. Farmers must stay in the Village (but they can be used for farming or spawning depending on wheat).
- Spawning mechanics: In the village, you can assign two villagers to "spawn farmer" with at least 10 wheat to create a new Farmer, and two villagers to "spawn warrior" with at least 12 wheat to create a new Warrior. The child villagers are spawned from the same village area, so they effectively stay in the Village.
- We must attack the Dragon early (at least once within the first 15 steps) and keep pressure on the Dragon by having enough warriors in the Cave.
- All Warriors should be in the Cave to attack. All Farmers should stay in the Village (but we can still use the spawn groups within the Village to grow the army).
- All Warriors should attack the Dragon after moving to the Cave. So in the Cave phase, Warriors should be assigned to an attack group, while Farmers should be returned to the Village.

Adaptation strategy:
- Village phase (assign_in_village):
  - Move all Warriors to the Cave to ensure they are in position to attack (assign to group "cave").
  - Keep Farmers in the Village by default (assign to group "farm" for regular farming).
  - Use spawning groups to grow the force when wheat is available:
    - If there are at least 4 Farmers and farm.wheat >= 10, assign 2 Farmers to "spawn farmer" to attempt generating at least one new Farmer.
    - If there are at least 2 Farmers left in the Village and farm.wheat >= 12, assign 2 to "spawn warrior" to attempt generating at least one new Warrior.
  - Assign any remaining Farmers to "farm" (continue farming).
- Cave phase (assign_in_cave):
  - Ensure all Warriors in the Cave are assigned to "attack" (these will attack the Dragon).
  - Any Farmers present in the Cave should be sent back to the Village (assign to "village"), since Farmers should stay in the Village.
  - This ensures all Warriors are positioned to attack and Farmers return to farming.
- This plan ensures:
  - All Warriors go to the Cave and attack (requirement).
  - All Farmers stay in the Village (moved back if they ever end up in the Cave).
  - Early Dragon attack is attempted by having Warriors in position early.
  - Spawning opportunities to create more Farmers and Warriors when wheat allows, so we have multiple units to contribute to the kill.
  - At least half of the warriors are in the Cave because all warriors are sent there in the Village phase and then assigned to attack in the Cave phase.

Python code (SmartAdaptation)

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Gather villagers currently in the Village
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # 1) Move all Warriors to the Cave (they will attack later)
        for w in warriors:
            environment.assign_group(w, "cave")

        # 2) Farm by default for all Farmers (stay in Village)
        remaining_farmers = list(farmers)

        # 3) Spawn opportunities (prefer some spawns if wheat available)
        # Spawn 1st: 2 farmers -> spawn farmer if wheat >= 10 and at least 4 farmers exist
        if len(remaining_farmers) >= 4 and getattr(environment.farm, "wheat", 0) >= 10:
            for _ in range(2):
                if remaining_farmers:
                    f = remaining_farmers.pop(0)
                    environment.assign_group(f, "spawn farmer")

        # 4) Spawn 2nd: 2 farmers left -> spawn warrior if wheat >= 12
        if len(remaining_farmers) >= 2 and getattr(environment.farm, "wheat", 0) >= 12:
            for _ in range(2):
                if remaining_farmers:
                    f = remaining_farmers.pop(0)
                    environment.assign_group(f, "spawn warrior")

        # 5) Assign any still remaining farmers to farming in village
        for f in remaining_farmers:
            environment.assign_group(f, "farm")

        # If there are any other components (unexpected), default them to farm
        assigned = set()
        for g in ["cave", "farm", "spawn farmer", "spawn warrior"]:
            # mark as assigned by collecting components already assigned in previous loops
            pass  # assignments are done per component directly below

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In Cave: Warriors should attack, Farmers should go back to Village
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:  # Farmer or any other role should return to Village
                environment.assign_group(c, "village")
```