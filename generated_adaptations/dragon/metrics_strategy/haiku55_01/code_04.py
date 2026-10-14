import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Maximize sustained damage on the Dragon:
    - Every Warrior goes to the Cave and attacks every step (no retreating).
    - Farmers stay in the Village, farm wheat, and are used in pairs to spawn
      new Warriors as often as wheat allows.
    """

    WARRIOR_WHEAT_COST = 12

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat

        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        # All warriors head to the Cave to attack.
        for w in warriors:
            environment.assign_group(w, "cave")

        # Number of Warrior spawns affordable this step:
        # each spawn needs a pair of farmers and 12 wheat.
        max_by_farmers = len(farmers) // 2
        max_by_wheat = wheat // self.WARRIOR_WHEAT_COST
        num_spawns = min(max_by_farmers, max_by_wheat)

        spawn_count = 2 * num_spawns
        for f in farmers[:spawn_count]:
            environment.assign_group(f, "spawn warrior")
        for f in farmers[spawn_count:]:
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.role == "Warrior":
                # Keep attacking regardless of HP: damage now shortens the fight.
                environment.assign_group(c, "attack")
            else:
                # Farmers are too fragile for the Cave; send them home.
                environment.assign_group(c, "village")