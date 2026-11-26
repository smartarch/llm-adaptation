import math
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step):
        if not components:
            return

        wheat = environment.farm.wheat
        dragon_hp = environment.dragon.hp

        # Priority 1: Must eat (steps_since_meal >= 4)
        eaters = [c for c in components if c.steps_since_meal >= 4]
        remaining = [c for c in components if c.steps_since_meal < 4]

        for c in eaters:
            environment.assign_group(c, "eat")

        if not remaining:
            return

        # Food demand estimate
        villagers_in_cave = len([v for v in environment.warriors if v.location == "Cave"]) + \
                            len([v for v in environment.farmers if v.location == "Cave"])
        total_villagers = len(environment.farmers) + len(environment.warriors)
        min_farmers = max(1, math.ceil(total_villagers / 30))

        # Categorize remaining by role
        farmers_rem = [c for c in remaining if c.role == "Farmer"]
        warriors_rem = [c for c in remaining if c.role == "Warrior"]

        # Minimum farmers stay farming
        farmers_farming = farmers_rem[:min_farmers]
        farmers_surplus = farmers_rem[min_farmers:]

        # Spawn warriors from surplus if possible
        wheat_reserve = max(villagers_in_cave, 5)
        available_wheat = max(0, wheat - wheat_reserve)
        max_spawnable = min(len(farmers_surplus) // 2, available_wheat // 12, 2)

        spawn_pool = farmers_surplus[:max_spawnable * 2]
        farmers_surplus = farmers_surplus[max_spawnable * 2:]

        for c in spawn_pool:
            environment.assign_group(c, "spawn warrior")

        # Send warriors to cave
        for c in warriors_rem:
            environment.assign_group(c, "cave")

        # Minimum farmers farm
        for c in farmers_farming:
            environment.assign_group(c, "farm")

        # Surplus farmers: farm for wheat, or attack if dragon is nearly dead
        if dragon_hp <= 15:
            for c in farmers_surplus:
                environment.assign_group(c, "cave")
        else:
            for c in farmers_surplus:
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        if not components:
            return

        dragon_hp = environment.dragon.hp

        # Split: must go eat vs can keep attacking
        need_food = [c for c in components if c.steps_since_meal >= 4]
        can_stay = [c for c in components if c.steps_since_meal < 4]

        # CRITICAL: Always ensure at least one villager attacks to prevent regen
        # If everyone needs food, keep the one with lowest steps_since_meal attacking
        if not can_stay and need_food:
            # Sort by steps_since_meal; keep the freshest one to attack
            need_food_sorted = sorted(need_food, key=lambda c: c.steps_since_meal)
            keep_attacking = need_food_sorted[0]
            send_to_village = need_food_sorted[1:]

            for c in send_to_village:
                environment.assign_group(c, "village")
            environment.assign_group(keep_attacking, "attack")
        else:
            # Normal case: send hungry ones back, rest attack
            for c in need_food:
                environment.assign_group(c, "village")
            for c in can_stay:
                environment.assign_group(c, "attack")