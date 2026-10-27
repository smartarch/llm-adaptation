

Looking at the 0% win rate, I need to fundamentally rethink the strategy. The key issues are:

1. **Warrior cycle timing**: A warrior's optimal cycle is 6 steps (eat→travel→attack×3→travel→eat), giving only 3 attacks per 6 steps. With 1 warrior, there are 3 steps of no attack per cycle, causing massive dragon regeneration.

2. **Need staggered warriors**: With 2 warriors offset by 3 steps, every step gets attacked. Need 3+ warriors for safety margin and enough total DPS to kill 100 HP.

3. **Spawning urgency**: Must spawn warriors ASAP using farmer pairs.

4. **Eating timing**: Warriors eating at sms=5 (arriving from cave) then immediately traveling = perfect 6-step cycle.

The critical fix: warriors in village with sms 0-1 should go to cave (arrive at sms 1-2, get 2-3 attacks). Warriors with sms >= 3 must eat. In cave, attack until sms=4, then return.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation
import abc


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.dragon_attacked = False

    def assign_in_village(self, components, environment, group_ids, step):
        dragon = environment.dragon
        farm = environment.farm
        wheat = farm.wheat

        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        # === WARRIOR ASSIGNMENTS ===
        # Rule: sms >= 3 must eat (can't go to cave - would arrive at 4+, can't attack)
        # Rule: sms 0-2 can go to cave (arrive at 1-3, can attack)
        for w in warriors:
            if w.steps_since_meal >= 3:
                environment.assign_group(w, "eat")
            else:
                environment.assign_group(w, "cave")

        # === FARMER ASSIGNMENTS ===
        # Must eat before starving: eat at sms >= 4 (safe margin)
        farmers_eat = [f for f in farmers if f.steps_since_meal >= 4]
        farmers_available = [f for f in farmers if f.steps_since_meal < 4]

        for f in farmers_eat:
            environment.assign_group(f, "eat")

        # === SPAWNING LOGIC ===
        # Aggressively spawn warriors early using farmer pairs
        # Need at least 2 farmers farming to maintain food supply
        # Each warrior spawn costs 2 farmers + 12 wheat
        # Each farmer spawn costs 2 farmers + 10 wheat

        num_available = len(farmers_available)
        min_farming = 2  # Keep at least 2 farmers farming

        # Determine how many pairs we can allocate to spawning
        excess = max(0, num_available - min_farming)
        max_pairs = excess // 2

        # Spawn strategy by phase
        if step <= 6:
            want_warriors = min(max_pairs, 2)
            want_farmers = 0
        elif step <= 14:
            want_warriors = min(max_pairs, 1)
            want_farmers = min(max_pairs - want_warriors, 1)
        elif step <= 20:
            want_warriors = min(max_pairs, 1) if wheat >= 12 else 0
            want_farmers = 0
        else:
            want_warriors = 0
            want_farmers = 0

        # Check wheat affordability
        actual_warrior_spawns = 0
        actual_farmer_spawns = 0
        wheat_budget = wheat

        for _ in range(want_warriors):
            if wheat_budget >= 12:
                actual_warrior_spawns += 1
                wheat_budget -= 12

        for _ in range(want_farmers):
            if wheat_budget >= 10:
                actual_farmer_spawns += 1
                wheat_budget -= 10

        # Assign farmers to groups
        sw_count = actual_warrior_spawns * 2
        sf_count = actual_farmer_spawns * 2

        idx = 0
        for f in farmers_available:
            if idx < sw_count:
                environment.assign_group(f, "spawn warrior")
            elif idx < sw_count + sf_count:
                environment.assign_group(f, "spawn farmer")
            else:
                environment.assign_group(f, "farm")
            idx += 1

    def assign_in_cave(self, components, environment, group_ids, step):
        dragon = environment.dragon

        for c in components:
            if c.steps_since_meal >= 4:
                # Must return to village NOW to eat in time
                # Arrive village next step at sms=5, eat then
                environment.assign_group(c, "village")
            else:
                # Safe to attack (sms 0-3)
                environment.assign_group(c, "attack")
```