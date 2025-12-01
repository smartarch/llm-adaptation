Reasoning and updated adaptation strategy

What we learned:
- The Dragon can retaliate in the Cave, potentially killing villagers. A naive strategy that sends all Warriors into the Cave at once is fast on paper but risky in practice.
- Spawning uses two villagers plus wheat (10 for Farmer spawns, 12 for Warrior spawns). Spawns do not consume villagers; they create new villagers while the two assigned for the spawn act as catalysts.
- We should balance speed ( DPS in the Cave ) with survivability ( fewer casualties per step and steady wheat income from Farmers).

New strategy (wave-based DPS with step-aware spawning and HP-aware gating)
- In the Village:
  - Move a small “attack wave” of Warriors into the Cave each step rather than sending all at once. This reduces the battlefield risk from dragon retaliation while still building DPS over time.
  - Farmers stay in the Village to farm and to enable spawning when wheat allows.
  - Spawning is step-gated and HP-gated:
    - Step 0-3: no spawns (focus on farming to build wheat).
    - Step 4-6: at most 1 spawn this step.
    - Step 7+: up to 2 spawns this step.
    - HP gating: if Dragon HP > 40, become more conservative; if Dragon HP < 25, allow a bit more aggression.
  - Spawn Farmers first (needs 2 Farmers and 10 wheat), then spawn Warriors (needs 2 Farmers and 12 wheat) if resources permit. Any remaining Warriors in village are kept in cave as part of the next-wave growth, not all at once.
- In the Cave:
  - Attack with a small, HP-aware wave of Warriors each step (instead of all-at-once). The rest of Warriors in cave stay put (continue in cave as a reserve) to reduce catastrophe risk, and Farmers return to the Village.

This approach aims for a smoother, more predictable growth of DPS in the Cave while maintaining wheat income for future spawns, increasing the likelihood of killing the Dragon within the 30-step limit.

Code implementation

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Divide villagers in the Village into:
        - farm: Stay in Village and farm
        - cave: Go to Cave (attack in the next step, in a gated wave)
        - spawn farmer: For every two villagers assigned to this group and 10 wheat, a new Farmer is spawned
        - spawn warrior: For every two villagers assigned to this group and 12 wheat, a new Warrior is spawned
        """
        # Separate farmers and warriors present in the village
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        villagers_warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Wave-based cave entry: move a small wave of Warriors to the Cave this step
        wave = 1 if step < 8 else 2  # escalate to 2 per step in later stages
        wave = min(wave, len(villagers_warriors))
        to_attack_now = villagers_warriors[:wave]

        for w in to_attack_now:
            environment.assign_group(w, "cave")

        # Remaining Warriors (if any) will stay in village this step (to be moved in future steps)
        remaining_warriors = villagers_warriors[wave:]

        # We still must assign the remaining Warriors somewhere this step. To keep growth predictable,
        # shift them into "spawn warrior" if wheat allows, otherwise put them in "cave" as reserve.
        # This preserves the wave concept without leaving villagers unassigned.
        wheat = int(getattr(environment.farm, "wheat", 0))
        max_spawns_step = 0
        if step < 4:
            max_spawns_step = 0
        elif step < 7:
            max_spawns_step = 1
        else:
            max_spawns_step = 2

        # HP gating
        dragon_hp = int(getattr(environment.dragon, "hp", 0))
        if dragon_hp > 40:
            max_spawns_step = max(0, max_spawns_step - 1)
        elif dragon_hp < 25:
            max_spawns_step = min(2, max_spawns_step + 1)

        # Try to spawn farmers first
        F = len(farmers)
        spawns_farmers = min(max_spawns_step, F // 2, wheat // 10)
        n_sf = spawns_farmers * 2
        wheat_after_farm = wheat - spawns_farmers * 10

        remaining_farmers = F - n_sf

        # Then try to spawn warriors if we have remaining farmers and wheat
        spawns_warriors = min(max_spawns_step - spawns_farmers, remaining_farmers // 2, wheat_after_farm // 12)
        n_sw = spawns_warriors * 2

        spawn_farmer_assignees = farmers[:n_sf]
        spawn_warrior_assignees = farmers[n_sf:n_sf + n_sw]
        farm_assignees = farmers[n_sf + n_sw:]

        for c in spawn_farmer_assignees:
            environment.assign_group(c, "spawn farmer")
        for c in spawn_warrior_assignees:
            environment.assign_group(c, "spawn warrior")
        for c in farm_assignees:
            environment.assign_group(c, "farm")

        # If there are any remaining warriors not assigned to spawn/attack this step, keep them in cave as reserve
        for w in remaining_warriors[n_sw:]:
            environment.assign_group(w, "cave")

        return

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Divide villagers in the Cave into:
        - attack: Attack the Dragon (wave-based)
        - cave: Stay in the Cave
        - village: Go to the Village
        """
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]

        # Determine how many warriors should attack this step (wave)
        dragon_hp = int(getattr(environment.dragon, "hp", 0))

        if dragon_hp <= 25:
            wave_size = min(3, len(warriors))
        elif dragon_hp <= 40:
            wave_size = min(2, len(warriors))
        else:
            wave_size = min(1, len(warriors))

        # Assign attack/wave to some warriors
        attack_candidates = warriors[:wave_size]
        remaining_in_cave = warriors[wave_size:]

        for c in attack_candidates:
            environment.assign_group(c, "attack")
        for c in remaining_in_cave:
            environment.assign_group(c, "cave")

        # Farmers in cave should head back to the Village
        for f in farmers:
            environment.assign_group(f, "village")
```