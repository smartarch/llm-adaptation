Reasoning and adaptation strategy (embedded as comments):

Goal
- Kill the Dragon as fast as possible while keeping villagers alive.
- Warriors should be used for combat; Farmers should stay in the village to farm and spawn new villagers when possible.

Key mechanics
- Farmers: HP 4, farm wheat 5, attack damage 1
- Warriors: HP 6, farm wheat 2, attack damage 3
- Spawn rules in village:
  - To spawn a new Farmer: for every two villagers assigned to "spawn farmer" and 10 wheat in the farm
  - To spawn a new Warrior: for every two villagers assigned to "spawn warrior" and 12 wheat in the farm
  - Spawn consumes wheat and two villagers in the corresponding spawn group
- Dragon: hp 50, can damage all villagers in cave (40% chance of 1 damage to each) or eat one random villager in cave (20%)
- Win condition: Dragon hp <= 0
- Lose condition: All villagers die or 30-step limit exceeded
- Villager groups:
  - Village: main area for farming
  - Cave: travel to fight
  - spawn farmer / spawn warrior: earmarked villagers to spawn new villagers using wheat
- Cave groups:
  - attack: attack the Dragon
  - cave: stay in cave
  - village: go back to Village

Strategy
1) In the village:
   - Send all Warriors to the cave (to reach and attack the Dragon).
   - Use Farmers to both farm and spawn new villagers when wheat (farm wheat) permits:
     - Compute spawns_farm = min(number_of_farmers // 2, wheat // 10)
     - Compute spawns_warrior = min((number_of_farmers - 2*spawns_farm) // 2, (wheat - 10*spawns_farm) // 12)
     - Assign first 2*spawns_farm Farmers to "spawn farmer"
     - Next 2*spawns_warrior Farmers to "spawn warrior"
     - Remaining Farmers to "farm"
2) In the cave:
   - All Warriors go to "attack"
   - Farmers return to the Village ("village")

Rationale
- Guarantees a steady influx of warriors to pressure the Dragon while keeping a growing base of Farmers to generate wheat for future spawns.
- Spawns are constrained by current wheat, ensuring we don’t overspend and can continue farming.
- By moving Warriors to the cave early, we maximize damage output early, accelerating time to kill the Dragon.

Python code:

```py
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
```