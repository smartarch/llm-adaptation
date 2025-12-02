```py
"""
Adaptation strategy (embedded as comments for clarity):

Goal:
- All Warriors should go to the Cave to attack the Dragon.
- All Farmers should stay in the Village, where they can farm or spawn new villagers.
- Use the two available spawn groups in the Village to dynamically grow our force:
  - "spawn farmer": For every two villagers assigned here and 10 wheat, a new Farmer is spawned.
  - "spawn warrior": For every two villagers assigned here and 12 wheat, a new Warrior is spawned.
  - The two villagers assigned to a spawn group are the spawners; spawning does not remove them.
  - We prioritize spawning Farmers (more wheat-efficient) to maximize population growth, then Warriors if wheat allows.
- In the Cave, move Warriors to "attack" to fight the Dragon, and move Farmers back to the Village via "village" so they can farm/spawn.
- This simple heuristic ensures a steady production of villagers and keeps combatant Warriors in the cave.

Rationale:
- Farmers are more wheat-efficient for spawning (requires 10 wheat per 1 new Farmer) than Warriors (12 wheat per 1 new Warrior). Thus, we first allocate spawners to spawning Farmers.
- Always funnel Warriors toward the Cave to fight the Dragon; keep Farmers in the Village unless they serve as spawn nodes.
- The strategy is robust to varying wheat stockpiles and villager counts, and respects the exact group naming requirements.

Implementation notes:
- In assign_in_village:
  - Gather Farmers and Warriors.
  - Compute how many "spawn farmer" groups we can support: min(nf // 2, wheat // 10).
  - With remaining Farmers and Wheat, compute how many "spawn warrior" groups: min((nf - 2*sf) // 2, (wheat - 10*sf) // 12).
  - Assign two spawners per spawn group, remaining Farmers go to "farm".
  - All Warriors go to "cave".
- In assign_in_cave:
  - Move all Warriors to "attack".
  - Move all Farmers to "village" (to return to the Village for farming/spawning).
"""

from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Classify villagers in the Village by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        nf = len(farmers)
        wheat = getattr(environment.farm, "wheat", 0)

        # Spawn farmers: need 2 villagers + 10 wheat per farmer spawned
        max_fspawn = min(nf // 2, wheat // 10)

        # Remaining farmers after assigning spawners for farmers
        remaining_farmers_after_fspawn = nf - max_fspawn * 2
        wheat_after_fspawn = wheat - max_fspawn * 10

        # Spawn warriors: need 2 villagers + 12 wheat per warrior spawned
        max_wspawn = min(remaining_farmers_after_fspawn // 2, wheat_after_fspawn // 12)

        # Total wheat consumed by spawns
        # wheat_used = max_fspawn * 10 + max_wspawn * 12

        # Assign spawners for farmers
        idx = 0
        for _ in range(max_fspawn * 2):
            if idx < len(farmers):
                environment.assign_group(farmers[idx], "spawn farmer")
                idx += 1

        # Assign spawners for warriors (these spawners are farmers by design)
        for _ in range(max_wspawn * 2):
            if idx < len(farmers):
                environment.assign_group(farmers[idx], "spawn warrior")
                idx += 1

        # Remaining farmers go to farming
        for j in range(idx, nf):
            environment.assign_group(farmers[j], "farm")

        # All warriors go to the cave to attack
        for w in warriors:
            environment.assign_group(w, "cave")

        # Note: If there are any farmers not processed due to list indexing, ensure they are assigned.
        # (This loop is a safety net; in normal flow all should be assigned above.)

        # If there were no farmers, still ensure warriors move to cave
        if nf == 0:
            for w in warriors:
                environment.assign_group(w, "cave")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave: Warriors go to attack, Farmers go back to Village
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            elif role == "Farmer":
                environment.assign_group(c, "village")
            else:
                # Fallback: keep them in cave if unknown role
                environment.assign_group(c, "cave")
```