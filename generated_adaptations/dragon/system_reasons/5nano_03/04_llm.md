Reasoning and strategy

Goal and constraints recap
- Kill the Dragon as fast as possible (Dragon HP = 50).
- All Warriors must go to the Cave and attack the Dragon.
- All Farmers should stay in the Village (but can be used to spawn new villagers or farm).
- Spawning rules:
  - spawn farmer: for every 2 villagers in this group and 10 wheat, a new Farmer is spawned.
  - spawn warrior: for every 2 villagers in this group and 12 wheat, a new Warrior is spawned.
- Dragon counterattacks can kill villagers in the Cave, so early, careful DPS is important.
- We must attack at least once within the first 15 steps and aim to have enough DPS to kill within 30 steps.

Strategy overview
- Early aggression with Warriors:
  - Move all existing Warriors to the Cave as soon as possible to ensure early attacks on the Dragon.
- Aggressive but cautious spawning using Farmers:
  - Use Farmers to spawn additional villagers to boost DPS, but only when wheat is available and we still have enough Farmers left to keep farming wheat for sustainment.
  - Prioritize spawning Farmers first (spawn farmer) to grow base population and Wheat production, then consider spawning Warriors (spawn warrior) cautiously, since spawning Warriors uses two farmers and reduces immediate farming capacity.
- Step-by-step allocation:
  - In assign_in_village:
    - Move all Warriors to cave.
    - For Farmers, compute how many can spawn Farmers (2 villagers per spawn, cost 10 wheat per spawn) given current wheat.
    - Use remaining Farmers (after farmer-spawns) to spawn Warriors (2 villagers per spawn, cost 12 wheat per spawn) if wheat allows.
    - Assign farmers to either:
      - spawn farmer (the two chosen for each farmer spawn),
      - spawn warrior (the two chosen for each warrior spawn),
      - farm (the rest stay in Village farming wheat).
  - In assign_in_cave:
    - All Warriors in Cave go to attack.
    - Farmers in Cave are returned to Village (to keep farming or spawning in future steps).

Why this can improve win rate
- Ensures early Dragon exposure by all Warriors.
- Increases population and wheat production early via farming spawns, enabling more future spawns and higher DPS.
- Balances immediate attack with population growth to sustain longer battles.
- Keeps Farmers in Village by default (as required) while still leveraging spawns to build more combatants over time.

Python implementation

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Identify villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # 1) Move all existing Warriors to the Cave for early DPS
        for w in warriors:
            environment.assign_group(w, "cave")

        # 2) Decide spawning allocations for Farmers
        # Wheat available in the Farm
        wheat = getattr(environment.farm, "wheat", 0)

        # How many farmer-spawns can we support? (2 farmers per spawn, 10 wheat per spawn)
        max_spawn_farm = 0
        if len(farmers) >= 2 and wheat >= 10:
            max_spawn_farm = min(len(farmers) // 2, wheat // 10)

        # After farmer-spawns, remaining farmers that can be allocated elsewhere
        remaining_farmers_after_farm_spawns = len(farmers) - 2 * max_spawn_farm
        wheat_after_farm_spawns = wheat - max_spawn_farm * 10

        # How many warrior-spawns can we support? (2 farmers per spawn, 12 wheat per spawn)
        max_spawn_warrior = 0
        if remaining_farmers_after_farm_spawns >= 2 and wheat_after_farm_spawns >= 12:
            max_spawn_warrior = min( remaining_farmers_after_farm_spawns // 2,
                                     wheat_after_farm_spawns // 12 )

        # 3) Assign groups for Farmers
        # First 2*max_spawn_farm farmers -> 'spawn farmer'
        # Next 2*max_spawn_warrior farmers -> 'spawn warrior'
        # Rest -> 'farm'
        for idx, f in enumerate(farmers):
            if idx < 2 * max_spawn_farm:
                environment.assign_group(f, "spawn farmer")
            elif idx < 2 * max_spawn_farm + 2 * max_spawn_warrior:
                environment.assign_group(f, "spawn warrior")
            else:
                environment.assign_group(f, "farm")

        # Warriors were already sent to the cave above; no further action needed here.

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave: attack with Warriors; Farmers return to Village
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```