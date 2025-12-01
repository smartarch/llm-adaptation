Reasoning and updated adaptation strategy

Goal recap (for clarity):
- Warriors must go to the Cave and attack the Dragon.
- Farmers stay in the Village to farm and/or spawn new villagers.
- Spawning costs: 2 villagers + 10 wheat for a Farmer, or 2 villagers + 12 wheat for a Warrior.
- The Dragon can retaliate in the Cave (40% to damage every villager in the Cave by 1; 20% to eat one random villager in the Cave). If all villagers die, you lose.
- You win by killing the Dragon (50 HP) within 30 steps.

What we learned from prior attempts:
- Large, uncoordinated waves into the Cave are fast but risky because Retrofit damage can wipe out villagers.
- Spawning is a critical capability to sustain wheat income (Farmers) and to increase DPS (Warriors). Spawning should be paced and gated by both step and Dragon HP to avoid wasteful early spawns or overcommitment when the Dragon is very strong.
- Farmers should generally stay in the Village to maximize wheat production; Warriors should be used to accumulate DPS in the Cave, but not in a single monstrous wave.

New, more cautious strategy (step- and HP-aware, wave-based DPS)
- Wave-based DPS in the Cave: send a small, controlled wave of Warriors each step (start with 1, raise to 2 in later steps if safe).
- Step gating for spawning:
  - Steps 0-2: no spawning (focus on growing wheat).
  - Steps 3-5: up to 1 spawn this step.
  - Steps 6+: up to 2 spawns this step.
- HP gating for spawning:
  - If Dragon HP > 40, be more conservative (lower max spawns).
  - If Dragon HP < 25, allow a bit more aggressive spawning (to finish sooner).
- Spawning priority:
  - Spawn Farmers first (needs 2 villagers and 10 wheat) to boost wheat production.
  - If wheat and villagers permit, spawn Warriors (needs 2 villagers and 12 wheat) to increase DPS.
- Villagers not assigned to the current attack wave or spawning should be assigned to farming to maintain wheat income.
- Cave handling:
  - Attack with a small, HP-aware wave (fewer casualties when HP is high; more when HP is low and we’re close to victory).
  - Farmers in the Cave are moved back to the Village.

Code implementation
- The following Python code implements this conservative, wave-based strategy with explicit step- and HP-aware gating. It ensures all villagers are assigned to some group each step and follows the required group names.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Village policy:
        - Send a small wave of Warriors to the Cave (attack) this step.
        - Use a step- and HP-aware budget to spawn Farmers first, then Warriors, using only villagers in the Village as catalysts.
        - Remaining villagers default to farming to grow wheat.
        Groups:
        - farm: Stay in Village and farm
        - cave: Go to Cave (attack in next step via a wave)
        - spawn farmer: For every two villagers assigned to this group and 10 wheat, a new Farmer is spawned
        - spawn warrior: For every two villagers assigned to this group and 12 wheat, a new Warrior is spawned
        """
        # Collect villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        village_warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Wave-based cave entry: move a small wave of Warriors to the Cave this step
        wave = 1
        if step >= 6:
            wave = 2
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

        # Compute spawns (use villagers in village as catalysts; we prefer farmers as catalysts)
        pool = [c for c in farmers]  # catalysts we can confidently use for spawns
        F = len(pool)

        # Spawn Farmers first (requires 2 catalysts and 10 wheat)
        spawns_farmers = min(max_spawns, F // 2, wheat // 10)
        n_sf = spawns_farmers * 2
        wheat_after_farm = wheat - spawns_farmers * 10

        # Remaining catalysts for potential Warrior spawns
        remaining_pool = F - n_sf
        spawns_warriors = min(max_spawns - spawns_farmers, remaining_pool // 2, wheat_after_farm // 12)
        n_sw = spawns_warriors * 2

        # Assign villagers to groups
        spawn_farmer_assignees = pool[:n_sf]
        spawn_warrior_assignees = pool[n_sf:n_sf + n_sw]
        farm_assignees = pool[n_sf + n_sw:]

        for c in spawn_farmer_assignees:
            environment.assign_group(c, "spawn farmer")
        for c in spawn_warrior_assignees:
            environment.assign_group(c, "spawn warrior")
        for c in farm_assignees:
            environment.assign_group(c, "farm")

        # If there are remaining Warriors not used for current wave, assign them to future-use path
        for w in remaining_warriors:
            # If we still have wheat to spare and spawns are possible, queue them for spawning;
            # otherwise, keep them in cave as a reserve by assigning them to "cave".
            if wheat > 12 and len(farmers) >= 2:
                environment.assign_group(w, "spawn warrior")
            else:
                environment.assign_group(w, "cave")

        # If there are any farmers not used in spawning, they would naturally be assigned to 'farm' above.
        # This ensures every component gets an assignment.
        return

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Cave policy:
        - Attack with a small, HP-aware wave of Warriors.
        - Move Farmers back to the Village.
        - Remaining Warriors stay in the Cave as reserve for future waves.
        """
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

        # Farmers in cave head back to the Village
        for f in farmers:
            environment.assign_group(f, "village")
```

Notes and expected effects:
- The wave-based DPS (1 then 2 per step) reduces the risk of catastrophic casualties from Dragon retaliation while still making progress toward killing the Dragon.
- Spawning is gated by step and Dragon HP, ensuring wheat is used efficiently and that we only grow when it makes sense to accelerate the finish.
- Farmers are prioritized for spawns to keep wheat production growing, with Warriors spawned only when there are enough catalysts and enough wheat.
- All villagers are assigned to a group each step, avoiding unassigned components.

If you want me to tailor further (for example, a different balance between early wheat growth vs. early DPS, or a strict 30-step cap with a hard DPS target), I can adjust the strategy and code accordingly.