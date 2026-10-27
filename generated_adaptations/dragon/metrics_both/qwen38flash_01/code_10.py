from generated_adaptations.base_classes.dragon import DragonHuntAdaptation
import abc


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step):
        wheat = environment.farm.wheat

        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        # === WARRIORS: optimal 3-attack / 6-step cycle ===
        for c in warriors:
            if c.steps_since_meal <= 1:
                environment.assign_group(c, "cave")
            else:
                environment.assign_group(c, "eat")

        # === FARMERS: eat at >=4 to prevent emergency, spawn warriors, farm rest ===
        free_farmers = []
        for c in farmers:
            if c.steps_since_meal >= 4:
                environment.assign_group(c, "eat")
            else:
                free_farmers.append(c)

        # Spawning: use up to (len-1)//2 farmers so at least 1 farms
        # Affordable pairs = wheat // 12 (wheat is pre-deduction snapshot)
        max_spawn_pairs = min(
            max(0, (len(free_farmers) - 1) // 2),
            int(wheat) // 12
        )

        for i in range(max_spawn_pairs):
            environment.assign_group(free_farmers[2 * i], "spawn warrior")
            environment.assign_group(free_farmers[2 * i + 1], "spawn warrior")

        # All remaining free farmers: farm to produce wheat
        for i in range(2 * max_spawn_pairs, len(free_farmers)):
            environment.assign_group(free_farmers[i], "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        warriors = [c for c in components if c.role == "Warrior"]

        # Farmers in cave (edge case): return to village
        for c in components:
            if c.role == "Farmer":
                environment.assign_group(c, "village")

        if not warriors:
            return

        # Attack while steps_since_meal <= 3; return at >= 4
        must_return = [c for c in warriors if c.steps_since_meal >= 4]
        can_attack = [c for c in warriors if c.steps_since_meal <= 3]

        # Stagger: prevent all warriors leaving simultaneously (dragon regen guard)
        if not can_attack and must_return:
            must_return.sort(key=lambda c: c.steps_since_meal)
            keeper = must_return.pop(0)
            can_attack.append(keeper)

        for c in can_attack:
            environment.assign_group(c, "attack")

        for c in must_return:
            environment.assign_group(c, "village")