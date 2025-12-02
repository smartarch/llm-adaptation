Reasoning and strategy plan:
- Goal: further reduce the number of turns to defeat the Dragon while keeping the risk from the Dragon’s attacks manageable.
- Core idea: keep all Warriors in the Cave to contribute DPS early, but accelerate the growth of the village by spawning Farmers and, as wheat allows, spawning Warriors sooner rather than later.
- Balancing act:
  - Spawn Farmers aggressively (to boost long-term wheat production and future spawns), but cap the number per step to avoid starving the cave of enough villagers to attack quickly.
  - Spawn Warriors earlier than before when there is enough wheat and enough Farmers available to spare, to increase DPS quickly without overwhelming the cave with non-farmers.
  - Always send Warriors to the Cave (attack) and send Farmers back to the Village when possible to resume farming/spawning in the next steps.
- Implementation notes:
  - We compute the maximum possible Farmer spawns given current wheat and farmers, cap it at a reasonable limit (e.g., 5 per step).
  - We compute Warrior spawns from the remaining Farmers after allocating Farmer spawns, with an early-step cap (e.g., up to 2 at step <= 3, up to 4 thereafter) and constrained by available wheat (12 per Warrior spawn).
  - This approach aims to get a higher DPS earlier (via Warriors) while sustaining wheat growth (via Farmers), reducing total turns to kill the Dragon.

Code (single Python code block):

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate villagers by role present in the Village
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Move all Warriors to the Cave so they can start attacking the Dragon
        for c in warriors:
            environment.assign_group(c, "cave")

        # Wheat available in the Farm
        wheat = getattr(getattr(environment, "farm", None), "wheat", 0)

        # Maximum possible Farmer spawns this step (2 farmers per spawn, 10 wheat per spawn)
        max_farm_spawns = min(len(farmers) // 2, wheat // 10)
        # Cap aggressive farming to keep risk manageable
        sF = min(max_farm_spawns, 5)

        spawn_farmers = farmers[:2 * sF]
        remaining_farmers = farmers[2 * sF:]

        # Remaining wheat after Farmer spawns
        wheat_rem = wheat - 10 * sF

        # Determine Warrior spawns from remaining farmers
        sW = 0
        if len(remaining_farmers) >= 2 and wheat_rem >= 12:
            if step <= 3:
                sW = min(len(remaining_farmers) // 2, 2, wheat_rem // 12)
            else:
                sW = min(len(remaining_farmers) // 2, 4, wheat_rem // 12)

        spawn_warriors = remaining_farmers[:2 * sW]
        remaining_farmers_after = remaining_farmers[2 * sW:]

        # Assign groups accordingly
        for c in spawn_farmers:
            environment.assign_group(c, "spawn farmer")
        for c in spawn_warriors:
            environment.assign_group(c, "spawn warrior")
        for c in remaining_farmers_after:
            environment.assign_group(c, "farm")

        # Note: All non-spawning farmers remain farming; all Warriors are in the cave already.

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the cave, Warriors attack; Farmers return to the Village
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```