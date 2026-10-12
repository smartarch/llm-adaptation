from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Partition villagers by role
        farmers = [c for c in components if getattr(c, 'role', None) == 'Farmer']
        warriors = [c for c in components if getattr(c, 'role', None) == 'Warrior']

        # Step 1: All Warriors go to the Cave
        for w in warriors:
            environment.assign_group(w, 'cave')

        # Step 2: Allocate Farmers to farming and spawning
        n_farmers = len(farmers)
        Wheat = getattr(environment.farm, 'wheat', 0)

        # First, determine how many farmers we can spawn as "spawn farmer"
        # Each spawn farmer requires 2 villagers and 10 wheat -> K = min(n_farmers//2, Wheat//10)
        k_farmers = min(n_farmers // 2, Wheat // 10)
        spawn_farmer_count = 2 * k_farmers
        Wheat_after_farmers = Wheat - (10 * k_farmers)

        # Assign the first 2*k_farmers farmers to "spawn farmer"
        for i in range(spawn_farmer_count):
            if i < n_farmers:
                environment.assign_group(farmers[i], 'spawn farmer')

        # Remaining farmers after allocating to spawn farmer
        idx = spawn_farmer_count
        remaining_farmers = n_farmers - idx

        # Next, determine how many of the remaining farmers we can use to spawn warriors
        # Each spawn warrior requires 2 villagers and 12 wheat -> K = min(remaining_farmers//2, Wheat_after_farmers//12)
        k_warriors = min(remaining_farmers // 2, Wheat_after_farmers // 12)
        spawn_warrior_count = 2 * k_warriors

        for i in range(spawn_warrior_count):
            if idx + i < n_farmers:
                environment.assign_group(farmers[idx + i], 'spawn warrior')

        idx += spawn_warrior_count
        # The rest of the farmers go to farming in the Village
        for j in range(idx, n_farmers):
            environment.assign_group(farmers[j], 'farm')

        # If there are no farmers, nothing else to do in this step

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave: Warriors attack, Farmers go back to Village
        for c in components:
            role = getattr(c, 'role', None)
            if role == 'Warrior':
                environment.assign_group(c, 'attack')
            elif role == 'Farmer':
                environment.assign_group(c, 'village')
            else:
                # Unknown role: keep safe by sending to Village
                environment.assign_group(c, 'village')