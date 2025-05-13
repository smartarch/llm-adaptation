import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        In the village we balance wheat production with the need to ramp up our warrior force.
        Early on when the dragon is still strong, we:
          - Have warriors use the 'spawn warrior' group if enough wheat (>= 12) is available,
            otherwise send them to the cave to start attacking.
          - Direct farmers to 'farm' if wheat is low, or to 'spawn farmer' if wheat is abundant,
            ensuring we continue generating wheat.
        When the dragon is weakened (dragon.hp <= 30), we send everyone to the cave.
        """
        wheat = environment.wheat
        dragon_hp = environment.dragon.hp

        for villager in components:
            # When the dragon is still healthy, invest in building a strong force.
            if dragon_hp > 30:
                if villager.role == "Warrior":
                    # Use warriors to spawn more warriors if resources allow.
                    if wheat >= 12:
                        environment.assign_group(villager, "spawn warrior")
                    else:
                        # With limited wheat, get warriors into position by sending them to the cave.
                        environment.assign_group(villager, "cave")
                else:  # For farmers
                    if wheat < 100:
                        # Prioritize farming to boost wheat production.
                        environment.assign_group(villager, "farm")
                    else:
                        # With plenty of wheat, spawn more farmers to keep wheat generation robust.
                        environment.assign_group(villager, "spawn farmer")
            else:
                # In the endgame, send everyone to the cave to concentrate fire on the dragon.
                environment.assign_group(villager, "cave")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        In the cave we balance aggression with caution.
        Warriors are assigned to 'attack' for maximum damage,
        while farmers remain in 'cave' to be available without taking undue risk.
        Additionally, any villager with very low health (hp < 2) is recalled to the village.
        When the dragon is nearly defeated (dragon.hp < 20), all villagers are encouraged to attack.
        """
        dragon_hp = environment.dragon.hp

        for villager in components:
            if villager.hp < 2:
                # Recall vulnerable villagers to preserve lives.
                environment.assign_group(villager, "village")
            else:
                if dragon_hp < 20:
                    # In the final push, all villagers attack.
                    environment.assign_group(villager, "attack")
                else:
                    # Otherwise, have warriors take the lead while farmers remain cautious.
                    if villager.role == "Warrior":
                        environment.assign_group(villager, "attack")
                    else:
                        environment.assign_group(villager, "cave")
