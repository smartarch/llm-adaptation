from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat

        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        # All warriors go to the cave to attack
        for w in warriors:
            environment.assign_group(w, "cave")

        # Count current warriors (including the ones we just sent to cave)
        current_warriors = len(warriors)
        current_farmers = len(farmers)

        # Assign farmers: aggressive spawning strategy
        available_farmers = list(farmers)
        spawned_this_step_w = 0
        spawned_this_step_f = 0

        # Spawn warriors aggressively - keep at least 1 farmer farming
        # We want more than 2 warriors for fast dragon kill
        while len(available_farmers) >= 3 and wheat >= 12 and (current_warriors + spawned_this_step_w) < 8:
            parent1 = available_farmers.pop(0)
            parent2 = available_farmers.pop(0)
            environment.assign_group(parent1, "spawn warrior")
            environment.assign_group(parent2, "spawn warrior")
            wheat -= 12
            spawned_this_step_w += 1

        # Then spawn farmers to maintain production - keep at least 1 farming
        while len(available_farmers) >= 3 and wheat >= 10 and (current_farmers - 2 * spawned_this_step_w - 2 * spawned_this_step_f + spawned_this_step_f) >= 2:
            parent1 = available_farmers.pop(0)
            parent2 = available_farmers.pop(0)
            environment.assign_group(parent1, "spawn farmer")
            environment.assign_group(parent2, "spawn farmer")
            wheat -= 10
            spawned_this_step_f += 1

        # All remaining farmers go to farm
        for f in available_farmers:
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.role == "Warrior":
                # Warriors always attack the dragon
                environment.assign_group(c, "attack")
            elif c.role == "Farmer":
                # Farmers should not be in cave - send back to village
                environment.assign_group(c, "village")