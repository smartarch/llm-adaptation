from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Split farmers and warriors in village (before moving to cave)
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        farm_group = "farm"
        cave_group = "cave"
        spawn_farmer_group = "spawn farmer"
        spawn_warrior_group = "spawn warrior"

        # First, move all warriors to cave (they will be overridden in cave phase to attack)
        for w in warriors:
            environment.assign_group(w, cave_group)

        # Spawn planning among farmers
        F = len(farmers)
        W = getattr(environment.farm, "wheat", 0)

        # Determine Pf (number of farmer-spawns) and Pw (warrior-spawns) to maximize total spawns
        bestPf, bestPw = 0, 0
        bestScore = -1
        maxPf = F // 2
        for Pf in range(0, maxPf + 1):
            remWheat = W - 10 * Pf
            if remWheat < 0:
                continue
            remaining_farmers_after_pf = F - 2 * Pf
            Pw = min(remaining_farmers_after_pf // 2, remWheat // 12)
            if Pw < 0:
                Pw = 0
            score = Pf + Pw
            # Prefer larger spawns if equal score
            if score > bestScore or (score == bestScore and (Pf > bestPf or (Pf == bestPf and Pw > bestPw))):
                bestPf, bestPw = Pf, Pw
                bestScore = score

        Pf = bestPf
        Pw = bestPw

        # Allocate farmers to groups
        # First Pf farmer-spawns: need 2*Pf villagers
        farmers_for_fspawn = farmers[: 2 * Pf]
        # Next Pw warrior-spawns: need 2*Pw villagers
        start_wspawn = 2 * Pf
        farmers_for_wspawn = farmers[start_wspawn: start_wspawn + 2 * Pw]
        # Remaining farmers go to farming
        farmers_for_farm = farmers[start_wspawn + 2 * Pw :]

        # Assign groups
        for c in farmers_for_fspawn:
            environment.assign_group(c, spawn_farmer_group)
        for c in farmers_for_wspawn:
            environment.assign_group(c, spawn_warrior_group)
        for c in farmers_for_farm:
            environment.assign_group(c, farm_group)

        # Any remaining warriors (if any) should already be in cave from above.

        # Note: If there are any non-Farmer components (e.g., unexpected), ensure they stay in Village
        # We assign any remaining non-assigned villagers to farming by default
        assigned = set(farmers_for_fspawn) | set(farmers_for_wspawn) | set(farmers_for_farm)
        for c in components:
            if c not in assigned and getattr(c, "role", None) != "Warrior":
                environment.assign_group(c, farm_group)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In Cave, send all Warriors to attack, Farmers to village
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                # Farmers stay in Village
                environment.assign_group(c, "village")