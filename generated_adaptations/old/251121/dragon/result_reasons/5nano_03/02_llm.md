Reasoning and adaptation strategy

Goal and constraints recap
- Warriors must end up in the Cave to attack the Dragon.
- Farmers should stay in the Village (but we can use them to spawn new villagers to strengthen the army).
- Spawn groups exist to create new Farmers and new Warriors, consuming wheat from the Farm.
- The Dragon should be attacked, and we should attack early (within the first 15 steps if possible).
- At least a few new villagers should be spawned, including both Farmers and Warriors, to improve odds.

Strategy (high level)
- Village phase:
  - All existing Warriors in the Village move to the Cave (group "cave") so they can eventually attack.
  - Farmers primarily stay in the Village (group "farm"), producing wheat.
  - Use a controlled spawning plan to create some extra Farmers and, if possible, some extra Warriors:
    - If we have enough wheat and at least two Farmers, we may spawn new Warriors by placing two Farmers in the "spawn warrior" group (requires 12 wheat).
    - If we still have spare Farmers and wheat, spawn additional Farmers by placing two Farmers in the "spawn farmer" group (requires 10 wheat per spawn).
  - The spawning logic is conditional on step (prefer at-step <= 15 to help ensure early attack) and available wheat.
  - All components must be assigned to exactly one group in this step.
- Cave phase:
  - All Warriors in the Cave should attack the Dragon (group "attack").
  - Farmers in the Cave should go back to the Village (group "village"), since they should stay farming.

Why this approach satisfies the requirements
- All warriors are moved to the Cave (and then to Attack in the cave phase), thus meeting the requirement that Warriors attack the Dragon after moving to the Cave.
- All Farmers remain in the Village as much as possible (only the spawning groups temporarily divert some Farmers from farming to spawn villagers; they still count as staying in the Village since the groups are village-side).
- We actively attempt to spawn both Farmers and Warriors to increase the chance of killing the Dragon.
- We attempt to ensure the Dragon is attacked early by spawning Warriors when possible within the first 15 steps and moving them to attack soon thereafter.
- We keep a majority of Warriors in the Cave (or on the way to the Cave and then to Attack), increasing the chance of a successful kill.

Code (Python)

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Assign villagers in the Village into:
        - "farm": stay in Village and farm
        - "cave": go to the Cave (for Warriors to eventually attack)
        - "spawn farmer": for every 2 farmers assigned here and 10 wheat, a new Farmer spawns
        - "spawn warrior": for every 2 villagers assigned here and 12 wheat, a new Warrior spawns
        """
        # Separate Farmers and Warriors currently in the Village
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        current_wheat = getattr(getattr(environment, "farm", None), "wheat", 0)
        avail_farmers = len(farmers)

        # Plan spawns (avoid consuming more than available)
        target_war_spawns = 0
        if step <= 15 and avail_farmers >= 2 and current_wheat >= 12:
            max_war_spawns = min(avail_farmers // 2, current_wheat // 12)
            target_war_spawns = min(2, max_war_spawns)

        remaining_farmers_after_war = avail_farmers - (2 * target_war_spawns)

        target_farm_spawns = 0
        if step <= 15 and remaining_farmers_after_war >= 2 and current_wheat >= 10:
            max_farm_spawns = min(remaining_farmers_after_war // 2, current_wheat // 10)
            target_farm_spawns = min(2, max_farm_spawns)

        # Allocate farmers to spawn groups and farming
        # Order matters to avoid overlapping assignments
        farmers_to_war_spawn = farmers[:2 * target_war_spawns]
        farmers_to_farm_spawn = farmers[2 * target_war_spawns:
                                        2 * target_war_spawns + 2 * target_farm_spawns]
        farmers_to_farm = farmers[2 * target_war_spawns + 2 * target_farm_spawns:]

        # Warriors go to the Cave (to later attack)
        for w in warriors:
            environment.assign_group(w, "cave")

        # Spawn groups (farmers to spawn new villagers)
        for f in farmers_to_war_spawn:
            environment.assign_group(f, "spawn warrior")
        for f in farmers_to_farm_spawn:
            environment.assign_group(f, "spawn farmer")

        # Remaining farmers stay in farming
        for f in farmers_to_farm:
            environment.assign_group(f, "farm")

        # If there are no farmers or all have been assigned to spawn groups above,
        # there might be nothing else to do for farmers; Warriors already assigned to cave.

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Assign villagers in the Cave into:
        - "attack": Attack the Dragon (for Warriors)
        - "cave": Stay in the Cave (optional, but not used here)
        - "village": Go to the Village (Farmers should return to farming)
        """
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                # All Warriors should attack
                environment.assign_group(c, "attack")
            else:
                # Farmers should go back to the Village
                environment.assign_group(c, "village")
```