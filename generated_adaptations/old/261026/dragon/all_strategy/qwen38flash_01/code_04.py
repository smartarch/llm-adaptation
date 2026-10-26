from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.spawned_warriors = 0
        self.spawned_farmers = 0

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat

        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        # Warriors immediately head to the cave to start attacking
        for w in warriors:
            environment.assign_group(w, "cave")

        farmer_idx = 0

        # Aggressive warrior spawning: try to spawn up to 4 warriors
        # Each warrior needs 2 farmers + 12 wheat
        while self.spawned_warriors < 4 and farmer_idx + 2 <= len(farmers) and wheat >= 12:
            # Don't spawn if it would leave 0 farmers and we haven't spawned farmers yet
            if farmer_idx + 2 >= len(farmers) and self.spawned_farmers < 2:
                break
            environment.assign_group(farmers[farmer_idx], "spawn warrior")
            environment.assign_group(farmers[farmer_idx + 1], "spawn warrior")
            farmer_idx += 2
            wheat -= 12
            self.spawned_warriors += 1

        # Spawn farmers for sustainability: up to 2, but keep at least 1 for farming
        while self.spawned_farmers < 2 and farmer_idx + 2 <= len(farmers) - 1 and wheat >= 10:
            environment.assign_group(farmers[farmer_idx], "spawn farmer")
            environment.assign_group(farmers[farmer_idx + 1], "spawn farmer")
            farmer_idx += 2
            wheat -= 10
            self.spawned_farmers += 1

        # Remaining farmers farm
        for i in range(farmer_idx, len(farmers)):
            environment.assign_group(farmers[i], "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        dragon_hp = environment.dragon.hp

        warriors_in_cave = [c for c in components if c.role == "Warrior"]
        farmers_in_cave = [c for c in components if c.role == "Farmer"]

        # All warriors attack the dragon every step
        for w in warriors_in_cave:
            environment.assign_group(w, "attack")

        # Determine if farmers should help attack (emergency mode)
        # Estimate: current dps from warriors, remaining steps, dragon hp
        num_warriors_attacking = len(warriors_in_cave)
        current_dps = num_warriors_attacking * 3
        remaining_steps = 30 - step
        steps_needed = dragon_hp / max(current_dps, 1) if current_dps > 0 else float('inf')

        # Send farmers to attack if: running out of time, or dragon is nearly dead
        send_farmers = False
        if remaining_steps <= steps_needed:
            send_farmers = True
        if dragon_hp <= num_warriors_attacking * 3 * remaining_steps + len(farmers_in_cave):
            send_farmers = True

        for f in farmers_in_cave:
            if send_farmers and f.hp > 1:
                environment.assign_group(f, "attack")
            else:
                environment.assign_group(f, "village")