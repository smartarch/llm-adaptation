from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def assign_in_village(self, components, environment, group_ids, step):
        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]
        wheat = environment.farm.wheat
        dragon_hp = environment.dragon.hp

        # Endgame: if dragon is nearly dead, send everyone to cave to finish
        if dragon_hp <= 5 and step >= 5:
            for c in components:
                environment.assign_group(c, "cave")
            return

        # All warriors go to cave immediately to attack
        for w in warriors:
            environment.assign_group(w, "cave")

        remaining_farmers = list(farmers)

        # Aggressively spawn warriors whenever possible
        # Every 3rd spawn slot, prefer a farmer spawn to boost economy
        spawn_slot = step // 2  # roughly count spawn opportunities
        prefer_farmer = (spawn_slot % 3 == 2)  # every 3rd opportunity do a farmer

        if prefer_farmer and len(remaining_farmers) >= 2 and wheat >= 10 and len(farmers) > 2:
            environment.assign_group(remaining_farmers[0], "spawn farmer")
            environment.assign_group(remaining_farmers[1], "spawn farmer")
            remaining_farmers = remaining_farmers[2:]
        elif len(remaining_farmers) >= 2 and wheat >= 12:
            environment.assign_group(remaining_farmers[0], "spawn warrior")
            environment.assign_group(remaining_farmers[1], "spawn warrior")
            remaining_farmers = remaining_farmers[2:]
        elif len(remaining_farmers) >= 2 and wheat >= 10 and len(farmers) > 3:
            environment.assign_group(remaining_farmers[0], "spawn farmer")
            environment.assign_group(remaining_farmers[1], "spawn farmer")
            remaining_farmers = remaining_farmers[2:]

        # All remaining farmers work the farm to accumulate wheat
        for f in remaining_farmers:
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        dragon_hp = environment.dragon.hp
        warriors_in_cave = [c for c in components if c.role == "Warrior"]
        num_warriors = len(warriors_in_cave)

        for c in components:
            if c.role == "Warrior":
                # Only send back if critically low HP AND we have enough warriors
                # to maintain "at least half in cave" requirement
                if c.hp <= 1 and num_warriors > 2 and dragon_hp > 5:
                    environment.assign_group(c, "village")
                else:
                    # All warriors attack the Dragon
                    environment.assign_group(c, "attack")
            elif c.role == "Farmer":
                # Farmers in cave shouldn't be there; send them back to farm
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")