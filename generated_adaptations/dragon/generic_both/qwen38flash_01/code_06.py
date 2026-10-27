from generated_adaptations.base_classes.dragon import DragonHuntAdaptation
import abc


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step):
        dragon = environment.dragon
        farm = environment.farm
        wheat = farm.wheat

        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        # --- Warrior assignments in village ---
        # Requirement: warriors with steps_since_meal >= 3 must eat before going to cave
        # Warriors with steps_since_meal >= 5 MUST eat
        for w in warriors:
            if w.steps_since_meal >= 3:
                environment.assign_group(w, "eat")
            else:
                # Steps_since_meal 0,1,2: can go to cave and still have room to attack
                # With steps 0: travel(1), atk(2), atk(3), atk(4), atk(5), travel(6) - 4 attacks safe
                # With steps 1: travel(2), atk(3), atk(4), atk(5), travel(6) - 3 attacks safe  
                # With steps 2: travel(3), atk(4), atk(5), travel(6) - 2 attacks, risky
                if w.steps_since_meal <= 1:
                    environment.assign_group(w, "cave")
                else:
                    # steps_since_meal == 2: eat to be safe, then full cycle
                    environment.assign_group(w, "eat")

        # --- Farmer assignments ---
        # Separate farmers that must eat
        farmers_eat = [f for f in farmers if f.steps_since_meal >= 4]
        farmers_working = [f for f in farmers if f.steps_since_meal < 4]

        for f in farmers_eat:
            environment.assign_group(f, "eat")

        # Spawning logic - aggressive early game
        # We want at least 4 warriors total for sustained DPS
        # Spawning costs: 2 villagers + 12 wheat (warrior) or 10 wheat (farmer)
        # Keep at least 2 farmers farming for food production
        
        num_working = len(farmers_working)
        min_farming = 2

        # Determine spawn budget
        # Phase 1 (step 1-8): aggressively spawn warriors
        # Phase 2 (step 9-18): spawn mix
        # Phase 3 (step 19+): focus on farming/feeding, minimal spawning
        
        if step <= 8:
            desired_warrior_spawns = 2
            desired_farmer_spawns = 1
        elif step <= 16:
            desired_warrior_spawns = 1
            desired_farmer_spawns = 1
        else:
            desired_warrior_spawns = 0
            desired_farmer_spawns = 0

        # Check what we can afford with working farmers and wheat
        available_for_spawn = max(0, num_working - min_farming)
        # Can only spawn in pairs
        available_pairs = available_for_spawn // 2

        # Prioritize warrior spawns (DPS matters most)
        actual_warrior_spawns = 0
        actual_farmer_spawns = 0
        wheat_remaining = wheat

        for i in range(min(desired_warrior_spawns, available_pairs)):
            if wheat_remaining >= 12:
                actual_warrior_spawns += 1
                wheat_remaining -= 12

        remaining_pairs = available_pairs - actual_warrior_spawns
        for i in range(min(desired_farmer_spawns, remaining_pairs)):
            if wheat_remaining >= 10:
                actual_farmer_spawns += 1
                wheat_remaining -= 10

        # Assign working farmers
        sw_farmers = actual_warrior_spawns * 2
        sf_farmers = actual_farmer_spawns * 2

        idx = 0
        for f in farmers_working:
            if idx < sw_farmers:
                environment.assign_group(f, "spawn warrior")
            elif idx < sw_farmers + sf_farmers:
                environment.assign_group(f, "spawn farmer")
            else:
                environment.assign_group(f, "farm")
            idx += 1

    def assign_in_cave(self, components, environment, group_ids, step):
        dragon = environment.dragon
        farm = environment.farm

        # Warriors in cave: attack the Dragon!
        # Must return to village before starving
        # Safe to attack if steps_since_meal <= 4 (will arrive back at 5-6, eat at 6-7)
        # Must leave if steps_since_meal >= 4 (travel next step = 5, arrive village at 6, eat)
        
        for c in components:
            if c.role == "Warrior":
                if c.steps_since_meal >= 4:
                    # Must return to village NOW to eat in time
                    environment.assign_group(c, "village")
                else:
                    # Safe to attack (steps_since_meal 0-3)
                    environment.assign_group(c, "attack")
            else:
                # Farmers in cave (rare, from spawning or mistakes)
                # Return to village
                environment.assign_group(c, "village")