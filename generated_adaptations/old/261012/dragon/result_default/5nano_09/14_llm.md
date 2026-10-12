Reasoning and updated adaptation strategy

Goal recap:
- Warriors must go to the Cave and attack the Dragon.
- Farmers stay in the Village to farm and/or spawn new villagers.
- Spawning costs: 2 villagers + 10 wheat for a Farmer, or 2 villagers + 12 wheat for a Warrior.
- Dragon can retaliate in the Cave (40% chance to damage every villager there by 1; 20% chance to eat one random villager in the Cave). If all villagers die, you lose.
- We want to win faster with a robust plan that scales DPS in the Cave while keeping casualties low and sustaining wheat production.

What to improve:
- Previous strategies tended to push large waves into the Cave or spawn aggressively without explicit pacing, which raised casualty risk and/or wasted wheat.
- We now adopt a conservative, wave-based DPS plan with explicit step- and HP-aware gating for spawning. We also gate how many Warriors we move to the Cave each step to limit catastrophe risk from retaliation.

New strategy (defensive, wave-based DPS with HP-aware gating)
- Village
  - Deploy a small attack wave to the Cave each step (start with 1 Warrior per step; escalate later if safe).
  - Farmers stay in the Village to farm and to enable spawning when wheat allows.
  - Spawning is step-gated and HP-gated:
    - Step 0-2: no spawns to stabilize wheat.
    - Step 3-5: at most 1 spawn this step.
    - Step 6+: up to 2 spawns this step.
    - If Dragon HP > 40, reduce spawning aggressiveness; if Dragon HP < 25, allow a bit more aggression.
  - Spawn Farmers first (needs 2 Farmers and 10 wheat), then spawn Warriors (needs 2 Farmers and 12 wheat) if resources permit. Use only farmers as the catalysts for spawns (consistent with prior convention).
  - Any remaining Warriors in the Village beyond the one sent to the Cave are routed to the “spawn warrior” route to incrementally build future spawns (keeps spawning capability alive without risking mass immediate combat).

- Cave
  - Attack with a conservative wave of Warriors (size depends on Dragon HP and current cave composition).
  - Move Farmers in the Cave back to the Village.
  - Keep the Cave wave size modest to reduce casualty risk from dragon retaliation, while still making progress.

This approach aims to:
- Maintain steady wheat income from Farmers for longer-term growth.
- Build DPS in the Cave gradually to minimize deaths due to retaliation.
- Adapt spawning intensity based on Dragon HP to avoid overcommitting when the Dragon is strong, and to push faster when it’s weak.

Code (Python)

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
        # Separate farmers and warriors present in the village
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        village_warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Wave-based cave entry: move a small wave of Warriors to the Cave this step
        wave = 1
        wave = 2 if step >= 8 else wave  # escalate a bit in later steps
        wave = min(wave, len(village_warriors))
        to_attack_now = village_warriors[:wave]

        for w in to_attack_now:
            environment.assign_group(w, "cave")

        # Remaining warriors in village (if any) will be handled for spawning or future waves
        remaining_warriors = village_warriors[wave:]

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

        # Compute spawns (spawns use farmers as catalysts)
        F = len(farmers)
        spawns_farmers = min(max_spawns, F // 2, wheat // 10)
        n_sf = spawns_farmers * 2
        wheat_after_farm = wheat - spawns_farmers * 10

        remaining_farmers = F - n_sf
        spawns_warriors = min(max_spawns - spawns_farmers, remaining_farmers // 2, wheat_after_farm // 12)
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

        # If there are remaining warriors not used for the current wave, keep them for future waves
        for w in remaining_warriors:
            # Heuristic: if wheat allows spawning, convert to a spawn warrior; otherwise hold in cave as reserve
            if wheat > 12 and len(farmers) >= 2:
                environment.assign_group(w, "spawn warrior")
            else:
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

        dragon_hp = int(getattr(environment.dragon, "hp", 0))

        # Determine attack wave size based on dragon HP and available warriors in cave
        total_warriors_in_cave = len(warriors)
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