import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step):
        wheat = environment.farm.wheat
        dragon_hp = environment.dragon.hp
        num_warriors = len(environment.warriors)
        num_farmers = len(environment.farmers)
        total = num_warriors + num_farmers

        # Endgame: everyone rushes to cave
        if dragon_hp <= 20:
            for c in components:
                environment.assign_group(c, "cave")
            return

        # 1) Anyone who needs to eat does so
        to_eat = [c for c in components if c.steps_since_meal >= 4]
        for c in to_eat:
            environment.assign_group(c, "eat")

        # 2) Remaining villagers
        remaining = [c for c in components if c.steps_since_meal < 4]
        farmers = [c for c in remaining if c.role == "Farmer"]
        warriors = [c for c in remaining if c.role == "Warrior"]

        # 3) All available warriors go to cave
        for w in warriors:
            environment.assign_group(w, "cave")

        # 4) Farmers: decide spawning vs farming
        # Spawn warriors aggressively, especially when low on warriors
        need_more_warriors = (num_warriors == 0) or (num_warriors < 4)

        # Calculate how many pairs of farmers we can spare for spawning
        # Keep at least 2 farmers farming to produce food (or all if fewer than 2)
        min_farming = min(2, len(farmers))
        spare = len(farmers) - min_farming
        max_pairs = spare // 2

        # Determine how many pairs we can afford
        pairs = 0
        if need_more_warriors or total < 5:
            reserve = total  # 1 wheat per villager for meals
            for p in range(1, max_pairs + 1):
                # Check if wheat covers p spawns + reserve for all villagers
                if wheat >= 12 * p + reserve:
                    pairs = p
                else:
                    break

        # Assign: first `pairs*2` farmers spawn warriors, rest farm
        for i in range(pairs * 2):
            environment.assign_group(farmers[i], "spawn warrior")
        for i in range(pairs * 2, len(farmers)):
            environment.assign_group(farmers[i], "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        dragon_hp = environment.dragon.hp

        for c in components:
            # Endgame: attack even if starving
            if dragon_hp <= 20:
                environment.assign_group(c, "attack")
            # Hunger: must leave to eat before starving
            elif c.steps_since_meal >= 4:
                # Travel 1 step (arrive s_m=5), next step eat (reset to 0)
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")