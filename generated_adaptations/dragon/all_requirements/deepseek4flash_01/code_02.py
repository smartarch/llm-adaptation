from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate farmers and warriors
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]
        
        # All warriors immediately go to the Cave
        for w in warriors:
            environment.assign_group(w, "cave")
        
        wheat = environment.farm.wheat
        dragon_hp = environment.dragon.hp
        
        spawn_warrior = False
        spawn_farmer = False
        
        if len(farmers) >= 2:
            if step < 10:
                # Early game: alternate to get both types quickly
                if step % 2 == 0:  # even steps: prioritize warrior
                    if wheat >= 12:
                        spawn_warrior = True
                    elif wheat >= 10:
                        spawn_farmer = True
                else:  # odd steps: prioritize farmer
                    if wheat >= 10:
                        spawn_farmer = True
                    elif wheat >= 12:
                        spawn_warrior = True
            elif dragon_hp < 20:
                # Dragon is weak: prioritize warriors to finish it
                if wheat >= 12:
                    spawn_warrior = True
                elif wheat >= 10:
                    spawn_farmer = True
            else:
                # Maintain a healthy farmer count, then spawn warriors
                if len(farmers) < 6 and wheat >= 10:
                    spawn_farmer = True
                elif wheat >= 12:
                    spawn_warrior = True
                elif wheat >= 10:
                    spawn_farmer = True
        
        # Assign farmers to spawn groups (at most 2 per step, using first two available)
        assigned_spawn = 0
        if spawn_warrior:
            for f in farmers[:2]:
                environment.assign_group(f, "spawn warrior")
            assigned_spawn = 2
        elif spawn_farmer:
            for f in farmers[:2]:
                environment.assign_group(f, "spawn farmer")
            assigned_spawn = 2
        
        # Remaining farmers work on the farm
        for f in farmers[assigned_spawn:]:
            environment.assign_group(f, "farm")
    
    def assign_in_cave(self, components, environment, group_ids, step: int):
        # All warriors attack the Dragon; farmers return to the Village
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")