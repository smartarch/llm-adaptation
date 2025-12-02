import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Split villagers into Farmers and Warriors
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # 1) All existing Warriors should go to the Cave
        for w in warriors:
            environment.assign_group(w, "cave")

        # 2) Distribute Farmers among farm / spawn farmer / spawn warrior
        total_farmers = len(farmers)

        spawn_farmer_count = 0
        spawn_warrior_count = 0
        farm_count = total_farmers  # default all to farming, may be reduced

        # Wheat available (read-only in this environment)
        wheat = getattr(getattr(environment, "farm", None), "wheat", 0)

        # Heuristic spawning plan to meet "a few" spawns
        if total_farmers >= 6 and wheat >= 24:
            # Aim for some farmer spawns and some warrior spawns
            spawn_farmer_count = min( max(2, total_farmers // 3), total_farmers - 2 )
            remaining = total_farmers - spawn_farmer_count
            # Try to spawn some warriors from the remaining pool if wheat allows
            if wheat >= 36 and remaining >= 2:
                spawn_warrior_count = min( max(1, remaining // 3), remaining - 1 )
            farm_count = total_farmers - spawn_farmer_count - spawn_warrior_count
        elif wheat >= 12 and total_farmers >= 4:
            # Moderate spawning: focus on warrior spawns if possible
            spawn_warrior_count = min(2, total_farmers - 2)
            farm_count = total_farmers - spawn_warrior_count

        # Assign Farmers to their groups
        idx = 0
        # spawn farmer
        for _ in range(spawn_farmer_count):
            if idx < total_farmers:
                environment.assign_group(farmers[idx], "spawn farmer")
                idx += 1
        # spawn warrior
        for _ in range(spawn_warrior_count):
            if idx < total_farmers:
                environment.assign_group(farmers[idx], "spawn warrior")
                idx += 1
        # keep remaining as farmers who farm
        for _ in range(farm_count):
            if idx < total_farmers:
                environment.assign_group(farmers[idx], "farm")
                idx += 1

        # If there are farmers left unassigned due to mismatch, assign them to farm by default
        while idx < total_farmers:
            environment.assign_group(farmers[idx], "farm")
            idx += 1

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave, send Warriors to attack, Farmers return to Village
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                # Farmers should stay in the Village
                environment.assign_group(c, "village")