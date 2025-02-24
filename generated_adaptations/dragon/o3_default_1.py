from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def assign_in_village(self, components, environment, step: int):
        # Total villagers available in the village
        total = len(components)
        wheat = environment.wheat
        dragon_hp = environment.dragon.hp

        # Set baseline ratios for group assignments.
        # If wheat is high and Dragon is still robust, we invest in spawning warriors.
        if wheat >= 50 and dragon_hp > 100:
            # Aggressive: spawn extra warriors to damage the Dragon fast.
            spawn_warrior_ratio = 0.15  # 15% of villagers (must be an even number)
            spawn_farmer_ratio = 0.05   # minimal farmer spawning
            cave_ratio = 0.40           # send many to the cave to join the attack
            farm_ratio = 0.40           # the rest work on the farm
        else:
            # When wheat is low or the Dragon is near defeat, focus on production and gradual re-balancing.
            spawn_warrior_ratio = 0.05
            spawn_farmer_ratio = 0.10
            cave_ratio = 0.30
            farm_ratio = 0.55

        # Calculate initial counts for each group
        spawn_warrior_count = int(total * spawn_warrior_ratio)
        spawn_farmer_count = int(total * spawn_farmer_ratio)
        cave_count = int(total * cave_ratio)
        # Ensure that all villagers are assigned
        farm_count = total - (spawn_warrior_count + spawn_farmer_count + cave_count)

        # Adjust spawn counts to be even (since 2 villagers yield a spawn)
        if spawn_warrior_count % 2 != 0 and spawn_warrior_count > 0:
            spawn_warrior_count -= 1
        if spawn_farmer_count % 2 != 0 and spawn_farmer_count > 0:
            spawn_farmer_count -= 1

        # Distribute assignments.
        # The order below prioritizes spawn groups first, then sending villagers to the cave, then working on the farm.
        for comp in components:
            if spawn_warrior_count > 0:
                environment.assign_group(comp, "spawn warrior")
                spawn_warrior_count -= 1
            elif spawn_farmer_count > 0:
                environment.assign_group(comp, "spawn farmer")
                spawn_farmer_count -= 1
            elif cave_count > 0:
                environment.assign_group(comp, "cave")
                cave_count -= 1
            else:
                environment.assign_group(comp, "farm")
                farm_count -= 1

    def assign_in_cave(self, components, environment, step: int):
        dragon_hp = environment.dragon.hp

        # In the cave, we want Warriors to actively attack when the Dragon is still strong.
        # Farmers, being less effective in combat, are sent back to the village.
        # Additionally, if the Dragon's hp is low (i.e. near defeat), we may hold some units in the cave.
        for comp in components:
            if comp.role == "Warrior":
                # If the Dragon is still a significant threat, warriors aggressively attack.
                if dragon_hp > 50:
                    environment.assign_group(comp, "attack")
                else:
                    # With a weakened Dragon, hold position in the cave.
                    environment.assign_group(comp, "cave")
            else:
                # Farmers are not meant for combat; send them back to the village.
                environment.assign_group(comp, "village")
