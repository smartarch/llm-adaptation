from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Heuristic strategy in the village:
         - In early steps (step < 10), focus on accumulating wheat and building up forces.
         - Use available wheat to spawn warriors (the more effective attackers) when possible.
         - Balance assignments between farming and sending some villagers toward the cave.

        Assignment details:
         - For every two villagers and if enough wheat is available (≥12), assign a pair to "spawn warrior".
         - The remaining villagers are split: if early in the game, roughly half work the farm (to gather wheat) and half move toward the cave.
         - In later steps (step >= 10), be more aggressive: send more villagers to the cave (to finish the Dragon) while still farming if wheat is in short supply.
        """
        total = len(components)
        assignments = {}

        # Count available pairs for spawning warriors based on wheat and number of villagers
        max_pairs = total // 2
        affordable_pairs = environment.wheat // 12
        spawn_pairs = min(max_pairs, affordable_pairs)
        spawn_count = spawn_pairs * 2

        # Decide split for non-spawn villagers:
        remaining = total - spawn_count

        # In early steps, more wheat production is desired.
        if step < 10:
            # Approximately half to farm, half to cave.
            farm_count = remaining // 2
            cave_count = remaining - farm_count
        else:
            # Later, more villagers should attack.
            # Use a 30%/70% split: 30% for farming, 70% for cave.
            farm_count = remaining * 30 // 100
            cave_count = remaining - farm_count

        # Assign first spawn_count villagers to spawn warrior (spawn pairs)
        idx = 0
        for comp in components:
            if idx < spawn_count:
                environment.assign_group(comp, "spawn warrior")
            elif idx < spawn_count + farm_count:
                environment.assign_group(comp, "farm")
            else:
                environment.assign_group(comp, "cave")
            idx += 1

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Heuristic strategy in the cave:
         - Warriors are best suited for attacking, so they are sent to the "attack" group.
         - Farmers are less robust and are less effective in battle, so in normal conditions
           they remain in the "cave" group to support (and to avoid being targeted).
         - However, when the Dragon is near death (hp < 15), even farmers are ordered to attack.
         - Villagers with low health (hp <= 2) are withdrawn back to the village for survival.
        """
        for comp in components:
            # If a villager is nearly dead, send back to village for safety.
            if comp.hp <= 2:
                environment.assign_group(comp, "village")
            else:
                # When the Dragon is nearly dead, even farmers help with the attack.
                if environment.dragon.hp < 15:
                    environment.assign_group(comp, "attack")
                else:
                    # Warriors focus on attacking.
                    if comp.role == "Warrior":
                        environment.assign_group(comp, "attack")
                    else:
                        # Farmers remain in cave (stay back).
                        environment.assign_group(comp, "cave")
