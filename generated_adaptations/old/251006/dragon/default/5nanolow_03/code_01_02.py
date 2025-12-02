import abc
from typing import List
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Divide Villagers in the Village into:
        - "farm": stay in Village and farm
        - "cave": go to Cave (to be attacked by cave logic in next step)
        - "spawn farmer": for every two villagers assigned here and 10 wheat, spawn a Farmer
        - "spawn warrior": for every two villagers assigned here and 12 wheat, spawn a Warrior
        """
        # Prepare containers
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Default: all farmers stay in the village and farm
        # We'll collect which farmers go to spawn groups
        to_spawn_farmers = []
        to_spawn_warriors = []

        # Current wheat available
        wheat = getattr(environment, "farm").wheat if hasattr(environment, "farm") else 0
        # Step 1: assign all farmers to "farm" by default
        for c in farmers:
            environment.assign_group(c, "farm")

        # Step 2: Determine spawns using farmers as resources for spawning
        # We will use farmers themselves as the pool to assign to spawn groups.
        # Available pool for spawning equals number of farmers (we'll take from the existing farmers)
        available_for_spawning = len(farmers)

        # Spawn farmers: need 2 villagers and 10 wheat per spawn
        max_possible_farm_spawns = wheat // 10
        s_f = min(available_for_spawning // 2, max_possible_farm_spawns)

        # Assign 2*s_f farmers to "spawn farmer"
        if s_f > 0:
            # pick 2*s_f farmers
            pick_count = 2 * s_f
            for c in farmers[:pick_count]:
                environment.assign_group(c, "spawn farmer")
            to_spawn_farmers = farmers[:pick_count]

            # Update wheat used
            wheat -= s_f * 10

        # After using some farmers for spawning farmers, update remaining pool
        remaining_farmers = farmers[0:]  # all farmers still considered for further spawning
        # We exclude those we just moved to spawn farmer
        if to_spawn_farmers:
            remaining_farmers = farmers[pick_count:]
        else:
            remaining_farmers = farmers

        # Spawn warriors: need 2 villagers and 12 wheat per spawn
        max_possible_war_spawns = wheat // 12
        s_w = min(len(remaining_farmers) // 2, max_possible_war_spawns)

        if s_w > 0:
            pick_count_w = 2 * s_w
            for c in remaining_farmers[:pick_count_w]:
                environment.assign_group(c, "spawn warrior")
            to_spawn_warriors = remaining_farmers[:pick_count_w]
            wheat -= s_w * 12

        # Any remaining farmers that were not assigned to spawn groups stay in farm
        # Warriors: they should go to cave in the cave step; ensure we also place any Warriors not yet assigned
        for w in warriors:
            # If a Warrior was accidentally assigned elsewhere due to previous steps, re-assign to cave in village phase
            environment.assign_group(w, "cave")

        # Finally, ensure farmers are not placed in cave in village step
        for c in farmers:
            environment.assign_group(c, "farm")

        # Note: The actual environment will interpret "spawn farmer"/"spawn warrior" groups to create new villagers
        # at the next game step. We have explicitly re-assigned all components above.

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Divide Villagers in the Cave into:
        - "attack": Attack the Dragon
        - "cave": Stay in the Cave
        - "village": Go to the Village
        """
        # Clear previous groupings in cave
        for c in components:
            # Default: put everyone into cave stayaged unless they are Warriors (which must attack)
            environment.assign_group(c, "cave")

        # Warriors should attack the Dragon
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")

        # Farmers should stay in Village
        for c in components:
            if getattr(c, "role", None) == "Farmer":
                environment.assign_group(c, "village")