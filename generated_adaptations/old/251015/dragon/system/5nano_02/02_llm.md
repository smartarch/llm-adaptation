"""
Reasoning and adaptation strategy (embedded as comments):

Goal
- Minimize dragon kill time and keep villagers alive for as long as possible.
- Warriors should be used for combat; Farmers should stay in the village to farm and
  to enable spawning of new villagers when wheat is available.

Basic rules recap
- Farmers: HP 4, farm wheat 5, attack damage 1
- Warriors: HP 6, farm wheat 2, attack damage 3
- Spawn mechanic (in village):
  - To spawn a new Farmer: for every two villagers assigned to the "spawn farmer" group and 10 wheat.
  - To spawn a new Warrior: for every two villagers assigned to the "spawn warrior" group and 12 wheat.
  - Each spawn consumes the required wheat and uses two villagers in that spawn group.
- Dragon: hp starts at 50, can deal 1 damage to every villager in cave with 40% probability, or eat one random villager in cave with 20% probability.
- Victory condition: Dragon hp <= 0, lose if any step count exceeds 30 or all villagers die.
- Groups in village:
  - "farm": farmers stay in village and farm
  - "cave": send villagers to cave
  - "spawn farmer": use two villagers in this group plus 10 wheat to spawn a new farmer
  - "spawn warrior": use two villagers in this group plus 12 wheat to spawn a new warrior
- Groups in cave:
  - "attack": attack the Dragon
  - "cave": stay in cave
  - "village": go back to village

Strategy
1) Village phase (assign_in_village)
   - All Warriors go to "cave" (to travel to the cave and eventually fight).
   - Farmers are used to farm or to spawn new villagers. We'll balance farming and spawning:
     - Compute maximum possible spawns for Farmers:
       spawns_farm = min(number_of_farmers // 2, wheat // 10)
     - From the remaining farmers, compute possible Warrior spawns (to increase combat force later):
       spawns_warrior = min((number_of_farmers - 2*spawns_farm) // 2, (wheat - 10*spawns_farm) // 12)
     - Assign the first 2*spawns_farm farmers to "spawn farmer",
       next 2*spawns_warrior farmers to "spawn warrior",
       and the rest to "farm".
   - This yields new farmers over time to strengthen both farming and future combat capability, while ensuring all Warriors are in the cave.

2) Cave phase (assign_in_cave)
   - All Warriors should attack: group "attack".
   - All Farmers should stay in the village: group "village".
   - No need to use the "cave" group in cave, unless desired by future rules; we keep farmers in the village.

3) Why this helps
   - Maintains a steady stream of new villagers via farming so the army can grow, while ensuring Warriors reach the cave to deal higher damage early.
   - Uses wheat to spawn as many villagers as possible given current numbers, balancing between immediate farming needs and long-term army growth.
   - Keeps Farmers in the village for farming to accumulate wheat for future spawns, which can accelerate reinforcement of both farmers and warriors over time.

Now the Python implementation.

"""

from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Divide villagers in the village into:
        - farm: Farmers who stay and farm
        - cave: All Warriors go to the Cave (travel)
        - spawn farmer: subset of Farmers used to spawn new Farmers
        - spawn warrior: subset of Farmers used to spawn new Warriors
        """
        # Separate farmers and warriors present in the village
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Step 1: Send all warriors to the cave (to later attack)
        for w in warriors:
            environment.assign_group(w, "cave")

        # Step 2: Compute spawn allocations from farmers based on available wheat
        total_farmers = len(farmers)
        available_wheat = getattr(environment.farm, "wheat", 0)

        spawns_farm = min(total_farmers // 2, available_wheat // 10)

        remaining_wheat_after_farms = available_wheat - spawns_farm * 10

        # Step 3: Compute possible warrior spawns from the remaining farmers
        spawns_warrior = min((total_farmers - 2 * spawns_farm) // 2,
                             remaining_wheat_after_farms // 12)

        # Step 4: Assign farmers to the appropriate spawn/farm groups
        # We will allocate in order: first 2*spawns_farm to "spawn farmer",
        # next 2*spawns_warrior to "spawn warrior", the rest to "farm".
        spawn_farmer_count = 2 * spawns_farm
        spawn_warrior_count = 2 * spawns_warrior

        # Ensure we don't overshoot if counts are misaligned
        spawn_farmer_set = farmers[:spawn_farmer_count]
        remaining_for_warriors = farmers[spawn_farmer_count:]
        spawn_warrior_set = remaining_for_warriors[:spawn_warrior_count]
        farm_set = remaining_for_warriors[spawn_warrior_count:]

        for c in spawn_farmer_set:
            environment.assign_group(c, "spawn farmer")
        for c in spawn_warrior_set:
            environment.assign_group(c, "spawn warrior")
        for c in farm_set:
            environment.assign_group(c, "farm")

        # Note: If there are any farmers not in the above groups (edge cases),
        # they will have been assigned to the last farm_set. Warriors already moved.

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Divide villagers in the cave into:
        - attack: Warriors attack the Dragon
        - cave: Stay in the Cave (if any)
        - village: Go back to Village (Farmers return to farming)
        """
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                # Farmers return to village to farm or spawn new villagers
                environment.assign_group(c, "village")