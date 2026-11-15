from generated_adaptations.base_classes.dragon import DragonHuntAdaptation
import abc


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.first_attack = False

    def assign_in_village(self, components, environment, group_ids, step):
        wheat = environment.farm.wheat

        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        # Priority 1: MUST EAT (steps_since_meal >= 5)
        must_eat_ids = set()
        for c in components:
            if c.steps_since_meal >= 5:
                environment.assign_group(c, "eat")
                must_eat_ids.add(id(c))

        # Remaining warriors (not forced to eat)
        remaining_warriors = [c for c in warriors if id(c) not in must_eat_ids]

        # Warriors: eat if getting hungry, otherwise go to cave
        warriors_eat = []
        warriors_cave = []
        for c in remaining_warriors:
            if c.steps_since_meal >= 3:
                warriors_eat.append(c)
            else:
                warriors_cave.append(c)

        for c in warriors_eat:
            environment.assign_group(c, "eat")
        for c in warriors_cave:
            environment.assign_group(c, "cave")

        # Farmers: eat, spawn, or farm
        remaining_farmers = [c for c in farmers if id(c) not in must_eat_ids]

        # Farmers that should eat soon (plan ahead to avoid emergencies)
        farmers_eat = [c for c in remaining_farmers if c.steps_since_meal >= 3]
        farmers_other = [c for c in remaining_farmers if c.steps_since_meal < 3]

        for c in farmers_eat:
            environment.assign_group(c, "eat")

        # Spawning logic
        # Priority: spawn warriors early for attack power, then balance with farmers
        spawn_pool = list(farmers_other)

        if step <= 8 and len(spawn_pool) >= 2 and wheat >= 12:
            # Early game: spawn warriors aggressively
            environment.assign_group(spawn_pool[0], "spawn warrior")
            environment.assign_group(spawn_pool[1], "spawn warrior")
            spawn_pool = spawn_pool[2:]
            # Try to spawn a second pair if we have enough
            if len(spawn_pool) >= 2 and wheat >= 24:
                environment.assign_group(spawn_pool[0], "spawn warrior")
                environment.assign_group(spawn_pool[1], "spawn warrior")
                spawn_pool = spawn_pool[2:]

        elif step <= 20 and len(spawn_pool) >= 2 and wheat >= 12:
            # Mid game: keep spawning warriors
            environment.assign_group(spawn_pool[0], "spawn warrior")
            environment.assign_group(spawn_pool[1], "spawn warrior")
            spawn_pool = spawn_pool[2:]

        elif step >= 5 and len(spawn_pool) >= 2 and wheat >= 10:
            # Spawn a farmer for more wheat production
            environment.assign_group(spawn_pool[0], "spawn farmer")
            environment.assign_group(spawn_pool[1], "spawn farmer")
            spawn_pool = spawn_pool[2:]
            # Also try to spawn a warrior if we have resources
            if len(spawn_pool) >= 2 and wheat >= 22:
                environment.assign_group(spawn_pool[0], "spawn warrior")
                environment.assign_group(spawn_pool[1], "spawn warrior")
                spawn_pool = spawn_pool[2:]

        # All remaining farmers: farm
        for c in spawn_pool:
            environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        # Farmers in cave (shouldn't happen but handle it): return to village
        for c in farmers:
            environment.assign_group(c, "village")

        # Warriors: attack or go to village to eat
        must_leave = [c for c in warriors if c.steps_since_meal >= 4]
        can_stay = [c for c in warriors if c.steps_since_meal < 4]

        # Safety: if no warrior can stay and at least one must leave,
        # keep the one with the lowest steps_since_meal to attack
        # (they'll be at 5 next step and go to village then)
        # This ensures dragon is not left unattacked for >2 steps
        if not can_stay and must_leave:
            must_leave.sort(key=lambda c: c.steps_since_meal)
            keeper = must_leave.pop(0)
            environment.assign_group(keeper, "attack")

        for c in can_stay:
            environment.assign_group(c, "attack")

        for c in must_leave:
            environment.assign_group(c, "village")