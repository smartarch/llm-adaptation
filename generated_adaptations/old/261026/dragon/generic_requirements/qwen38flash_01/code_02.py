from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def assign_in_village(self, components, environment, group_ids, step):
        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        wheat = environment.farm.wheat
        assigned = set()

        # Requirement: All warriors go to the Cave to attack the Dragon
        for w in warriors:
            environment.assign_group(w, "cave")
            assigned.add(id(w))

        # Spawning: use pairs of farmers to spawn new units
        # Need 12 wheat for warrior, 10 for farmer
        # Schedule spawns at specific steps once wheat is available
        unassigned_farmers = [f for f in farmers if id(f) not in assigned]

        # Spawn warriors at steps 2, 5, 8 (to get more damage dealers)
        # Spawn farmers at steps 3, 6, 9 (to boost wheat production)
        spawn_warrior_steps = [2, 5, 8]
        spawn_farmer_steps = [3, 6, 9]

        did_spawn = False

        # Try to spawn a warrior (2 villagers + 12 wheat)
        if step in spawn_warrior_steps and len(unassigned_farmers) >= 2 and wheat >= 12:
            for i in range(2):
                environment.assign_group(unassigned_farmers[i], "spawn warrior")
                assigned.add(id(unassigned_farmers[i]))
            unassigned_farmers = unassigned_farmers[2:]
            did_spawn = True
        # Try to spawn a farmer (2 villagers + 10 wheat)
        elif step in spawn_farmer_steps and len(unassigned_farmers) >= 2 and wheat >= 10:
            for i in range(2):
                environment.assign_group(unassigned_farmers[i], "spawn farmer")
                assigned.add(id(unassigned_farmers[i]))
            unassigned_farmers = unassigned_farmers[2:]
            did_spawn = True

        # All remaining farmers work on the farm
        for f in farmers:
            if id(f) not in assigned:
                environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        dragon_hp = environment.dragon.hp

        for c in components:
            if c.role == "Warrior":
                # Send critically low HP warriors back to preserve them for spawning pairs
                # Keep at least half attacking (requirement 8)
                if c.hp <= 1 and step > 5:
                    environment.assign_group(c, "village")
                else:
                    # All warriors attack the Dragon
                    environment.assign_group(c, "attack")
            elif c.role == "Farmer":
                # Farmers in cave should go back to village (all farmers stay in village)
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")