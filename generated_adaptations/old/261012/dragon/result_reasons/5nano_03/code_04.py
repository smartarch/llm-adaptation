from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate farmers and warriors present in the village
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Strategy: All Warriors should go to the Cave to attack the Dragon
        for w in warriors:
            environment.assign_group(w, "cave")

        # Spawning logic for farmers and warriors (spawn groups live in the village)
        wheat = getattr(environment.farm, "wheat", 0)
        remaining_farmers = list(farmers)

        # Early steps prioritize aggressive warrior spawning to boost early damage
        if step <= 5:
            # Spawn as many Warriors as possible first (needs 2 farmers per spawn, 12 wheat)
            while len(remaining_farmers) >= 2 and wheat >= 12:
                a = remaining_farmers.pop(0)
                b = remaining_farmers.pop(0)
                environment.assign_group(a, "spawn warrior")
                environment.assign_group(b, "spawn warrior")
                wheat -= 12

            # Then spawn Farmers if possible (needs 2 farmers per spawn, 10 wheat)
            while len(remaining_farmers) >= 2 and wheat >= 10:
                a = remaining_farmers.pop(0)
                b = remaining_farmers.pop(0)
                environment.assign_group(a, "spawn farmer")
                environment.assign_group(b, "spawn farmer")
                wheat -= 10
        else:
            # Later steps: favor farming first to grow wheat, then spawn as possible
            while len(remaining_farmers) >= 2 and wheat >= 10:
                a = remaining_farmers.pop(0)
                b = remaining_farmers.pop(0)
                environment.assign_group(a, "spawn farmer")
                environment.assign_group(b, "spawn farmer")
                wheat -= 10

            while len(remaining_farmers) >= 2 and wheat >= 12:
                a = remaining_farmers.pop(0)
                b = remaining_farmers.pop(0)
                environment.assign_group(a, "spawn warrior")
                environment.assign_group(b, "spawn warrior")
                wheat -= 12

        # Remaining farmers stay in the village to farm
        for f in remaining_farmers:
            environment.assign_group(f, "farm")

        # Note:
        # - All Warriors are directed to the cave (attack readiness).
        # - Farmers remain in the village, with the potential to spawn more villagers or farm.

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the cave: attack the Dragon with all Warriors; Farmers stay in the Village
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")