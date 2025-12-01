Reasoning and updated adaptation strategy

Goal recap:
- Warriors must go to the Cave and attack the Dragon.
- Farmers stay in the Village to farm and/or spawn new villagers.
- Spawning costs: 2 villagers + 10 wheat for a Farmer, or 2 villagers + 12 wheat for a Warrior.
- The Dragon can retaliate in the Cave (40% chance to damage every villager in the Cave by 1; 20% chance to eat one random villager in the Cave). If all villagers die, you lose.
- We want to win faster with a robust plan that scales DPS in the Cave while keeping casualties low and sustaining wheat production.

What to improve:
- Previous strategies spawned and moved forces with fixed heuristics that didn’t adapt well to the evolving situation (Dragon HP, Wheat, and risk of retaliation). We need a predictable, step-aware spawning policy that also uses Warriors more conservatively in the Cave to reduce casualties from retaliation.
- Spawn should ideally be done using villagers in the Village, with Farmers prioritized for wheat growth but not ignoring Warrior spawns when wheat is abundant. We should also ensure every Village unit gets assigned to a group each step.

New strategy (conservative, wave-based DPS with explicit gating)
- Village
  - Move a small attack wave of Warriors into the Cave each step (start with 1, possibly 2 in later steps). This yields a steady DPS without dumping all Warriors into the Cave at once.
  - Farmers stay in the Village to farm and to enable spawning when wheat allows.
  - Spawning is gated by step and Dragon HP:
    - Steps 0-2: no spawns (focus on accumulating wheat).
    - Steps 3-5: up to 1 spawn this step.
    - Steps 6+: up to 2 spawns this step.
    - HP gating: if Dragon HP > 40, reduce spawning; if HP < 25, allow a bit more aggressive spawning.
  - Spawns use any two villagers in the Village (not just Farmers). We favor spawning Farmers first (needs 2 villagers and 10 wheat) to boost wheat production, then spawn Warriors (needs 2 villagers and 12 wheat) if resources permit. This keeps population growth aligned with wheat income.
  - Any remaining villagers not used for spawning or attacking are assigned to farming (the "farm" group) to maintain wheat production.
- Cave
  - Attack with a small, controlled wave of Warriors (size depends on Dragon HP and available Warriors in the Cave).
  - Farmers in the Cave move back to the Village.
  - Avoid massive simultaneous assaults to limit casualties from retaliation.

This approach aims to:
- Maintain a steady wheat income from Farmers for longer-term spawning.
- Build DPS in the Cave gradually to minimize casualties from the Dragon’s retaliation while still making progress toward killing the Dragon within 30 steps.

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
        - cave: Go to Cave (attack in the next step, via a controlled wave)
        - spawn farmer: For every two villagers assigned to this group and 10 wheat, a new Farmer is spawned
        - spawn warrior: For every two villagers assigned to this group and 12 wheat, a new Warrior is spawned
        """
        # All villagers currently in the Village (Farmers and Warriors)
        villagers = list(components)

        # Wave-based cave entry: move a small wave of Warriors to the Cave this step
        # Default wave: 1, escalate to 2 in later steps
        wave = 1
        if step >= 6:
            wave = 2
        wave = min(wave, len([v for v in villagers if getattr(v, "role", None) == "Warrior"]))
        to_attack_now = [v for v in villagers if getattr(v, "role", None) == "Warrior"][:wave]

        for w in to_attack_now:
            environment.assign_group(w, "cave")

        # Remaining villagers in village after moving the attack wave
        remaining_in_village = [v for v in villagers if v not in to_attack_now]

        # Wheat and dragon HP influence spawning budget
        wheat = int(getattr(environment.farm, "wheat", 0))
        dragon_hp = int(getattr(environment.dragon, "hp", 0))

        # Step-based spawn budget (conservative early, ramp later)
        if step < 3:
            max_spawns = 0
        elif step < 6:
            max_spawns = 1
        else:
            max_spawns = 2

        # HP gating
        if dragon_hp > 40:
            max_spawns = max(0, max_spawns - 1)  # be conservative
        elif dragon_hp < 25:
            max_spawns = min(2, max_spawns + 1)  # allow a bit more aggression

        # Compute spawns (spawns use villagers in village as catalysts)
        pool = remaining_in_village
        F = len(pool)

        spawns_farmers = min(max_spawns, F // 2, wheat // 10)
        n_sf = spawns_farmers * 2
        wheat_after_farm = wheat - spawns_farmers * 10

        remaining_pool = F - n_sf
        spawns_warriors = min(max_spawns - spawns_farmers, remaining_pool // 2, wheat_after_farm // 12)
        n_sw = spawns_warriors * 2

        spawn_farmer_assignees = pool[:n_sf]
        spawn_warrior_assignees = pool[n_sf:n_sf + n_sw]
        farm_assignees = pool[n_sf + n_sw:]

        for c in spawn_farmer_assignees:
            environment.assign_group(c, "spawn farmer")
        for c in spawn_warrior_assignees:
            environment.assign_group(c, "spawn warrior")
        for c in farm_assignees:
            environment.assign_group(c, "farm")

        # If there are any remaining villagers in the village not used for spawning or attacking,
        # assign them to farming by default to keep wheat income growing.
        # (In this implementation, all remaining are already assigned above, but this is a safety net.)

        return

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Divide villagers in the Cave into:
        - attack: Attack the Dragon (wave-based)
        - cave: Stay in the Cave
        - village: Go to the Village
        """
        # Roles currently in the Cave
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]

        dragon_hp = int(getattr(environment.dragon, "hp", 0))
        total_warriors_in_cave = len(warriors)

        # Determine attack wave size based on dragon HP and available warriors
        if total_warriors_in_cave <= 0:
            wave_size = 0
        elif dragon_hp > 40:
            wave_size = 1
        elif dragon_hp > 25:
            wave_size = min(2, total_warriors_in_cave)
        else:
            wave_size = min(3, total_warriors_in_cave)

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