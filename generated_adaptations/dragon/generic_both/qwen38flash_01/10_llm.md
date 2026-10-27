

Looking at this problem, the previous strategy failed because:
1. **Dragon regeneration**: 5 HP/step when unattacked kills any 1-warrior cycle
2. **Warrior deaths**: 20% eat + 40% damage per attack makes long cave stays deadly
3. **Insufficient DPS pipeline**: Need ~4 warriors cycling continuously

**New Strategy**:
- Aggressive warrior spawning with farmer pairs from step 1
- Tight 6-step warrior cycle: eat→travel→attack×3→travel→eat (3 attacks)
- Warriors in cave attack unless sms ≥ 4 (then return) or HP very low
- Farmers always eat when sms ≥ 4; surplus farmers spawn warriors first, farmers second
- Keep only 1 farmer farming (each produces 5 wheat, plenty for food)
- HP-based safety: return warriors with HP ≤ 2

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation
import abc


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step):
        wheat = environment.farm.wheat

        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        # === WARRIOR ASSIGNMENTS ===
        # Priority 1: must eat to avoid starvation (sms >= 5)
        # Priority 2: eat proactively at sms >= 3 so they arrive in cave fed (sms 0-2)
        #             and can sustain 3 attacks before returning
        # Priority 3: otherwise send to cave to attack
        for w in warriors:
            if w.steps_since_meal >= 3:
                environment.assign_group(w, "eat")
            elif w.hp <= 2:
                # Too weak; eat and let hp recovery not be an issue,
                # but actually they need to rest too. Eat this step;
                # they'll still go out next step with full sms budget.
                # Actually hp doesn't regen. So just send them; they need to eat.
                # If they're at low HP, eating at sms=2 gives them sms 0 going out.
                environment.assign_group(w, "eat")
            else:
                environment.assign_group(w, "cave")

        # === FARMER ASSIGNMENTS ===
        # Step 1: separate must-eat farmers (sms >= 4 for safety; 5 = starving next step)
        must_eat = [f for f in farmers if f.steps_since_meal >= 4]
        can_work = [f for f in farmers if f.steps_since_meal < 4]

        for f in must_eat:
            environment.assign_group(f, "eat")

        # === SPAWNING LOGIC (aggressive, early game focused) ===
        # Each warrior spawn: 2 villagers in "spawn warrior" + 12 wheat
        # Each farmer spawn: 2 villagers in "spawn farmer" + 10 wheat
        # Keep at least 1 farmer farming (5 wheat/step, enough to feed everyone)
        num_can_work = len(can_work)
        min_farming = 1

        excess = max(0, num_can_work - min_farming)
        pairs = excess // 2

        # Phase-based spawn targets
        # Phase 1 (early, step 1-12): build up warrior force aggressively
        # Phase 2 (step 13-22): maintain and add a farmer if possible
        # Phase 3 (step 23+): stop spawning, focus on farming and attacking
        if step <= 12:
            target_warrior_spawns = min(pairs, 2)
            target_farmer_spawns = min(max(0, pairs - target_warrior_spawns), 1)
        elif step <= 22:
            target_warrior_spawns = min(pairs, 1)
            target_farmer_spawns = min(max(0, pairs - target_warrior_spawns), 1)
        else:
            target_warrior_spawns = 0
            target_farmer_spawns = 0

        # Affordability check
        actual_warrior = 0
        actual_farmer = 0
        remaining_wheat = wheat
        for _ in range(target_warrior_spawns):
            if remaining_wheat >= 12:
                actual_warrior += 1
                remaining_wheat -= 12
        for _ in range(target_farmer_spawns):
            if remaining_wheat >= 10:
                actual_farmer += 1
                remaining_wheat -= 10

        sw_farmers = actual_warrior * 2
        sf_farmers = actual_farmer * 2

        idx = 0
        for f in can_work:
            if idx < sw_farmers:
                environment.assign_group(f, "spawn warrior")
            elif idx < sw_farmers + sf_farmers:
                environment.assign_group(f, "spawn farmer")
            else:
                environment.assign_group(f, "farm")
            idx += 1

    def assign_in_cave(self, components, environment, group_ids, step):
        # Warriors in cave: attack aggressively.
        # Return to village if:
        #   - sms >= 4 (will reach village at sms 5, can eat before starving at 6)
        #   - hp <= 2 (too fragile to survive another counterattack)
        for c in components:
            if c.steps_since_meal >= 4 or c.hp <= 2:
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")
```