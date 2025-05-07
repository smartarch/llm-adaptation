from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        In the Village, our goal is to use each villager optimally:

        - Warriors are immediately sent to the Cave.
        - Farmers remain in the Village.
          * If there is abundant wheat (≥12 wheat), we try to spawn more Warriors,
            since they are crucial for the Dragon attack.
          * If wheat is moderately high (≥10 wheat but less than 12), we focus on spawning new Farmers.
          * Otherwise, the farmer works the fields to generate more wheat.

        Note: The spawn groups require two villagers plus the corresponding wheat threshold.
        """
        for comp in components:
            if comp.role == "Warrior":
                environment.assign_group(comp, "cave")
            elif comp.role == "Farmer":
                if environment.wheat >= 12:
                    environment.assign_group(comp, "spawn warrior")
                elif environment.wheat >= 10:
                    environment.assign_group(comp, "spawn farmer")
                else:
                    environment.assign_group(comp, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        In the Cave, the assignment is straightforward:

        - Warriors are ordered to attack the Dragon.
        - Farmers, who are not effective in combat, are sent back to the Village
          (if accidentally present in the Cave) so they can help generate wheat or spawn new villagers.
        """
        for comp in components:
            if comp.role == "Warrior":
                environment.assign_group(comp, "attack")
            else:  # comp.role == "Farmer"
                environment.assign_group(comp, "village")
