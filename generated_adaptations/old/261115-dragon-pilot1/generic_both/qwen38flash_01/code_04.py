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

        # --- Warrior assignments ---
        # Warriors must eat if steps_since_meal >= 3 (per requirements)
        # Otherwise they go to cave to attack
        for w in warriors:
            if w.steps_since_meal >= 3:
                environment.assign_group(w, "eat")
            else:
                environment.assign_group(w, "cave")

        # --- Farmer assignments ---
        # Separate farmers that must eat vs those that can work
        farmers_eat = []
        farmers_work = []

        for f in farmers:
            if f.steps_since_meal >= 5:
                farmers_eat.append(f)
            elif f.steps_since_meal >= 4:
                farmers_eat.append(f)
            else:
                farmers_work.append(f)

        for f in farmers_eat:
            environment.assign_group(f, "eat")

        # Spawn logic: assign pairs of working farmers to spawn groups
        # Keep at least 2 farmers farming to sustain wheat production
        # Prefer spawning warriors (for DPS), then farmers (for food)
        num_working = len(farmers_work)
        min_farming = 2  # minimum farmers to keep farming

        # Calculate how many spawn slots we can afford
        # Each spawn uses 2 farmers + wheat (12 for warrior, 10 for farmer)
        # Only spawn in early/mid game; in late game focus on attacking
        spawn_warrior_pairs = 0
        spawn_farmer_pairs = 0

        # Early game (step <= 15): aggressive spawning
        # Mid game (step 15-22): moderate spawning
        # Late game (step > 22): stop spawning, focus on farming for food
        if step <= 15:
            max_warrior_spawns = 2
            max_farmer_spawns = 1
        elif step <= 22:
            max_warrior_spawns = 1
            max_farmer_spawns = 1
        else:
            max_warrior_spawns = 0
            max_farmer_spawns = 0

        # Determine spawn counts based on available farmers and wheat
        potential_pairs = max(0, (num_working - min_farming)) // 2

        # Warrior spawns cost 12 wheat, farmer spawns cost 10 wheat
        # Budget: try warriors first, then farmers
        wheat_for_warriors = min(max_warrior_spawns, potential_pairs)
        actual_warrior_spawns = 0
        wheat_check = wheat
        for i in range(wheat_for_warriors):
            if wheat_check >= 12:
                wheat_check -= 12
                actual_warrior_spawns += 1

        remaining_pairs = potential_pairs - actual_warrior_spawns
        actual_farmer_spawns = 0
        for i in range(min(max_farmer_spawns, remaining_pairs)):
            if wheat_check >= 10:
                wheat_check -= 10
                actual_farmer_spawns += 1

        # Assign farmers to groups
        sw_count = actual_warrior_spawns * 2
        sf_count = actual_farmer_spawns * 2

        idx = 0
        for f in farmers_work:
            if idx < sw_count:
                environment.assign_group(f, "spawn warrior")
            elif idx < sw_count + sf_count:
                environment.assign_group(f, "spawn farmer")
            else:
                environment.assign_group(f, "farm")
            idx += 1

    def assign_in_cave(self, components, environment, group_ids, step):
        dragon = environment.dragon

        # Warriors in cave: attack unless they need to return to eat
        # If steps_since_meal >= 4, they must go back now (arrive at 5, eat next step)
        # If steps_since_meal >= 5, they are already starving - go back ASAP
        attack_list = []
        village_list = []

        for c in components:
            if c.steps_since_meal >= 4:
                # Must return to village to avoid starving
                village_list.append(c)
            else:
                # Safe to attack
                attack_list.append(c)

        for c in attack_list:
            environment.assign_group(c, "attack")
        for c in village_list:
            environment.assign_group(c, "village")