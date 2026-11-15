from generated_adaptations.base_classes.dragon import DragonHuntAdaptation
import abc


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step):
        wheat = environment.farm.wheat

        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        # --- WARRIORS in village ---
        # Primary cycle: eat at ssm>=2, cave at ssm<=1 (3 attacks per trip)
        # Early game (few warriors): also send ssm=2 warriors to cave
        #   so they attack at ssm=3 (arrive at cave ssm=3) → return at ssm=4
        #   This sacrifices 1 attack but gets body in cave faster
        # Once 3+ warriors exist, use strict ssm<=1 to maintain 3-attack cycles
        
        num_warriors_in_cave_or_heading = len(warriors)  # approx
        
        for c in warriors:
            if c.steps_since_meal <= 1:
                environment.assign_group(c, "cave")
            elif c.steps_since_meal == 2 and step <= 5:
                # Early rush: send even ssm=2 warriors to get more attackers
                environment.assign_group(c, "cave")
            else:
                environment.assign_group(c, "eat")

        # --- FARMERS ---
        # Eat at ssm>=5 to maximize wheat, but ensure they eat
        free = []
        for c in farmers:
            if c.steps_since_meal >= 5:
                environment.assign_group(c, "eat")
            else:
                free.append(c)

        # --- SPAWNING cascade ---
        remaining = list(free)

        if step <= 8 and len(remaining) >= 2 and wheat >= 12:
            environment.assign_group(remaining[0], "spawn warrior")
            environment.assign_group(remaining[1], "spawn warrior")
            remaining = remaining[2:]
            if len(remaining) >= 2 and wheat >= 24:
                environment.assign_group(remaining[0], "spawn warrior")
                environment.assign_group(remaining[1], "spawn warrior")
                remaining = remaining[2:]
            elif len(remaining) >= 2 and wheat >= 22:
                environment.assign_group(remaining[0], "spawn farmer")
                environment.assign_group(remaining[1], "spawn farmer")
                remaining = remaining[2:]

        elif step <= 20 and len(remaining) >= 2 and wheat >= 12:
            environment.assign_group(remaining[0], "spawn warrior")
            environment.assign_group(remaining[1], "spawn warrior")
            remaining = remaining[2:]

        elif step >= 5 and len(remaining) >= 2 and wheat >= 10:
            environment.assign_group(remaining[0], "spawn farmer")
            environment.assign_group(remaining[1], "spawn farmer")
            remaining = remaining[2:]
            if len(remaining) >= 2 and wheat >= 22:
                environment.assign_group(remaining[0], "spawn warrior")
                environment.assign_group(remaining[1], "spawn warrior")
                remaining = remaining[2:]

        for c in remaining:
            environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        warriors = [c for c in components if c.role == "Warrior"]

        # Farmers in cave: send back
        for c in components:
            if c.role == "Farmer":
                environment.assign_group(c, "village")

        if not warriors:
            return

        # Attack at ssm<=3, return at ssm>=4
        must_return = [c for c in warriors if c.steps_since_meal >= 4]
        can_attack = [c for c in warriors if c.steps_since_meal <= 3]

        # Stagger protection: never allow all warriors to leave simultaneously
        if not can_attack and must_return:
            must_return.sort(key=lambda c: c.steps_since_meal)
            keeper = must_return.pop(0)
            can_attack.append(keeper)

        for c in can_attack:
            environment.assign_group(c, "attack")

        for c in must_return:
            environment.assign_group(c, "village")