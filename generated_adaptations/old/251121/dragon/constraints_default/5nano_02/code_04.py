"""
Adaptation strategy (updated to ensure early Warrior spawning and robust assignment):

Goal:
- All Warriors should go to the Cave to attack the Dragon.
- All Farmers should stay in Village, farming or spawning new villagers.
- Use two spawn groups in the Village:
  - "spawn farmer": for every two villagers assigned to this group and 10 wheat, a new Farmer is spawned.
  - "spawn warrior": for every two villagers assigned to this group and 12 wheat, a new Warrior is spawned.
- The two villagers in a spawn group are the spawners; spawning consumes wheat and does not remove the spawners.
- Always move Warriors to the Cave for combat; Farmers stay in Village for farming/spawning.
- Strategy optimizes: spawn as many Farmers as possible (due to wheat efficiency), then spawn Warriors if wheat allows. If possible, attempt to spawn at least one Warrior early by rebalancing spawners when feasible.

Rationale:
- Prioritize Farmers (10 wheat per Farmer) to maximize long-term growth.
- Ensure at least a small number of Warriors spawn in early steps when resources permit, to improve dragon-hunting chances.
- All components must be assigned to exactly one valid group.

Implementation notes:
- In assign_in_village:
  - Count Farmers and Warriors present in the Village.
  - Compute max_fspawn and max_wspawn based on counts and current wheat.
  - If no Warrior spawns are possible but there is enough total potential to enable at least one Warrior by sacrificing one Farmer spawn, adjust by reducing max_fspawn by 1 and recomputing max_wspawn.
  - Assign two spawners to "spawn farmer" for each of max_fspawn, then two spawners to "spawn warrior" for each of max_wspawn (from Farmers list).
  - Remaining Farmers go to "farm"; All Warriors go to "cave".
- In assign_in_cave:
  - Warriors go to "attack"; Farmers go to "village".

This approach guarantees every component gets exactly one group, and increases the likelihood of spawning new Warriors early to improve Dragon kill prospects.
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

        # Fall-back: try to ensure at least one Warrior spawns if possible
        if max_wspawn == 0 and nf >= 4 and wheat >= 22:
            new_max_fspawn = max_fspawn - 1
            if new_max_fspawn >= 0:
                rem_f2 = nf - new_max_fspawn * 2
                wheat_after_fspawn2 = wheat - new_max_fspawn * 10
                max_wspawn2 = min(rem_f2 // 2, wheat_after_fspawn2 // 12)
                if max_wspawn2 >= 1:
                    max_fspawn = new_max_fspawn
                    max_wspawn = max_wspawn2

        # Assign spawners for farmers
        idx = 0
        for _ in range(max_fspawn * 2):
            if idx < len(farmers):
                environment.assign_group(farmers[idx], "spawn farmer")
                idx += 1

        # Assign spawners for warriors (these spawners come from farmers if available)
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

        # Safety: if there were no farmers, ensure warriors (if any) are in cave
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