import generated_adaptations.base_classes.dragon as base


class SmartAdaptation(base.DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        if not components:
            return

        wheat = environment.farm.wheat
        dragon_hp = environment.dragon.hp

        all_warriors = environment.warriors
        all_farmers = environment.farmers
        total_villagers = len(all_warriors) + len(all_farmers)

        warriors_in_cave = sum(1 for w in all_warriors if w.location == "Cave")
        farmers_in_cave = sum(1 for f in all_farmers if f.location == "Cave")

        # Priority 1: Feed villagers who are getting hungry (steps_since_meal >= 3)
        hungry = [c for c in components if c.steps_since_meal >= 3]
        rest = [c for c in components if c.steps_since_meal < 3]

        # Sort hungry by urgency (highest steps_since_meal first)
        hungry.sort(key=lambda c: c.steps_since_meal, reverse=True)

        wheat_remaining = wheat
        for c in hungry:
            if wheat_remaining > 0:
                environment.assign_group(c, "eat")
                wheat_remaining -= 1
            else:
                # No wheat available, must farm to produce some
                environment.assign_group(c, "farm")

        # Separate remaining villagers by role
        rem_farmers = [c for c in rest if c.role == "Farmer"]
        rem_warriors = [c for c in rest if c.role == "Warrior"]

        # Determine how many warriors we want attacking the dragon
        # Keep at least 1 warrior in village for spawning/rotation
        if dragon_hp <= 10:
            target_attack = len(all_warriors)  # Endgame: all warriors attack
        elif dragon_hp <= 30:
            target_attack = max(3, min(len(all_warriors), 6))
        else:
            target_attack = min(4, max(1, len(all_warriors)))

        need_in_cave = max(0, target_attack - warriors_in_cave)

        # Minimum farmers needed to sustain wheat production
        # Total wheat needed per step: ~total_villagers/6 (eating) + some surplus
        min_farm = max(1, (total_villagers + 5) // 6)

        # Spawning logic: early game (steps 1-6), only if enough wheat
        spawn_warrior_villagers = 0
        if step <= 6 and wheat_remaining >= 12 and len(rem_warriors) >= 2:
            # Assign pairs to spawn warrior
            spawn_count = min(4, len(rem_warriors))
            spawn_count -= spawn_count % 2  # Ensure even number
            if spawn_count >= 2:
                # Calculate how many pairs we can afford
                affordable_pairs = wheat_remaining // 12
                actual_spawn = min(spawn_count, affordable_pairs * 2)
                actual_spawn -= actual_spawn % 2

                for c in rem_warriors[:actual_spawn]:
                    environment.assign_group(c, "spawn warrior")
                rem_warriors = rem_warriors[actual_spawn:]
                spawn_warrior_villagers = actual_spawn
                wheat_remaining -= (actual_spawn // 2) * 12

        # Also try to spawn farmers in very early game if very few farmers
        if step <= 3 and wheat_remaining >= 10 and len(all_farmers) < 3 and len(rem_farmers) >= 2:
            farmer_spawn_count = min(2, len(rem_farmers))
            for c in rem_farmers[:farmer_spawn_count]:
                environment.assign_group(c, "spawn farmer")
            rem_farmers = rem_farmers[farmer_spawn_count:]
            wheat_remaining -= 10

        # Assign remaining warriors: send to cave or farm in village
        for c in rem_warriors:
            if need_in_cave > 0:
                environment.assign_group(c, "cave")
                need_in_cave -= 1
            else:
                # Keep in village to farm and eat (rest period)
                environment.assign_group(c, "farm")

        # Assign remaining farmers: farm (priority) or cave (endgame)
        farm_assigned = 0
        for c in rem_farmers:
            if farm_assigned < min_farm:
                environment.assign_group(c, "farm")
                farm_assigned += 1
            elif dragon_hp <= 15 and need_in_cave > 0:
                # Late game: send surplus farmers to cave for extra damage
                environment.assign_group(c, "cave")
                need_in_cave -= 1
            else:
                environment.assign_group(c, "farm")
                farm_assigned += 1

    def assign_in_cave(self, components, environment, group_ids, step: int):
        if not components:
            return

        dragon_hp = environment.dragon.hp

        # If dragon is dead or about to be, just stay and attack
        # Otherwise, manage the rotation for eating

        # Count how many are attacking to ensure we have minimum pressure
        # Priority: attack if safe, go to village if need to eat soon

        for c in components:
            if c.steps_since_meal >= 4:
                # Must go back to village: travel (1 step, hits 5) then eat next step
                # At threshold 4, they travel safely (arrive at 5, eat at next step)
                environment.assign_group(c, "village")
            elif c.steps_since_meal >= 5:
                # Very urgent (shouldn't normally reach here if threshold is 4)
                environment.assign_group(c, "village")
            elif dragon_hp <= 0:
                # Dragon is dead, go home
                environment.assign_group(c, "village")
            elif dragon_hp <= 10:
                # Endgame push: attack regardless of hunger (risk starvation for final blow)
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "attack")