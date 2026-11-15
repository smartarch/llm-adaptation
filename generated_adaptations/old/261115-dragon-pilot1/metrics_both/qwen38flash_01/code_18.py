from generated_adaptations.base_classes.dragon import DragonHuntAdaptation
import abc


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step):
        wheat = environment.farm.wheat

        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        # Warriors: strict optimal cycle - cave at ssm<=1, eat at ssm>=2
        # Arrives cave at ssm=1, attacks at 1,2,3, returns at 4, arrives village at 5, eats
        for c in warriors:
            if c.steps_since_meal <= 1:
                environment.assign_group(c, "cave")
            else:
                environment.assign_group(c, "eat")

        # Farmers: eat at ssm>=3 (faster cycling, more spawn availability)
        free = []
        for c in farmers:
            if c.steps_since_meal >= 3:
                environment.assign_group(c, "eat")
            else:
                free.append(c)

        # Aggressive warrior spawning - convert farmers to warriors ASAP
        remaining = list(free)

        if step <= 10 and len(remaining) >= 2 and wheat >= 12:
            # Early game: maximum warrior spawning
            environment.assign_group(remaining[0], "spawn warrior")
            environment.assign_group(remaining[1], "spawn warrior")
            remaining = remaining[2:]
            # Second pair if affordable
            if len(remaining) >= 2 and wheat >= 24:
                environment.assign_group(remaining[0], "spawn warrior")
                environment.assign_group(remaining[1], "spawn warrior")
                remaining = remaining[2:]
            # Third pair if wheat is plentiful
            if len(remaining) >= 2 and wheat >= 36:
                environment.assign_group(remaining[0], "spawn warrior")
                environment.assign_group(remaining[1], "spawn warrior")
                remaining = remaining[2:]
        elif step <= 20 and len(remaining) >= 2 and wheat >= 12:
            environment.assign_group(remaining[0], "spawn warrior")
            environment.assign_group(remaining[1], "spawn warrior")
            remaining = remaining[2:]
        elif step >= 5 and len(remaining) >= 2 and wheat >= 10:
            # Spawn a farmer to maintain wheat production
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

        for c in components:
            if c.role == "Farmer":
                environment.assign_group(c, "village")

        if not warriors:
            return

        # Attack at ssm<=3, return at ssm>=4
        must_return = [c for c in warriors if c.steps_since_meal >= 4]
        can_attack = [c for c in warriors if c.steps_since_meal <= 3]

        # Stagger: prevent all warriors leaving same step (dragon regen guard)
        if not can_attack and must_return:
            must_return.sort(key=lambda c: c.steps_since_meal)
            keeper = must_return.pop(0)
            can_attack.append(keeper)

        for c in can_attack:
            environment.assign_group(c, "attack")
        for c in must_return:
            environment.assign_group(c, "village")