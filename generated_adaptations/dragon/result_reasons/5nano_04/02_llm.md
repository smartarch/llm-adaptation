Reasoning and adaptation strategy

Goal recap and constraints
- Kill the Dragon as fast as possible. Dragon HP starts at 50; Warriors deal 3 damage, Farmers deal 1.
- Villagers come in two types: Farmers (HP 4, wheat 5 when farming, 1 damage when attacking) and Warriors (HP 6, wheat 2 when farming, 3 damage when attacking).
- Spawn mechanism: To spawn a new Villager, at least two villagers must be in a spawn group and enough wheat must be available:
  - Spawn Farmer: 2 villagers in "spawn farmer" group and 10 wheat -> +1 Farmer
  - Spawn Warrior: 2 villagers in "spawn warrior" group and 12 wheat -> +1 Warrior
- Dragon reacts: 40% chance to deal 1 damage to each villager in the Cave, 20% to eat one random villager in the Cave.

Strategic requirements to satisfy
- All Warriors should go to the Cave to attack the Dragon.
- All Farmers should stay in the Village (but can participate in spawning via their own spawn groups).
- Attack must happen at least once in the first 15 steps.
- Spawn both new Farmers and new Warriors (to increase total DPS) and keep at least half of the Warriors in the Cave most of the time.
- After moving to the Cave, all Warriors should attack the Dragon.

Adaptation plan
- In assign_in_village:
  - Move all Warriors to the Cave (group "cave"). This ensures they will be in the Cave for attack planning and aligns with the rule that all Warriors go to the Cave.
  - Keep Farmers in the Village by default (group "farm"), but also allocate some Farmers to spawn groups to generate more villagers:
    - Determine how many new Farmers (spawn Farmer) and new Warriors (spawn Warrior) can be spawned this step given the Wheat in the Farm.
    - For spawning, two Farmers must be assigned to the corresponding spawn group per spawn, and enough Wheat must be available (10 for Farmer spawn, 12 for Warrior spawn).
    - Implement a small early-game boost (step <= 10) to spawn a few extra villagers if wheat and farmers allow, to ensure we generate “a few” new villagers early for aiding the kill.
  - The remaining Farmers stay in the Village (group "farm").
- In assign_in_cave:
  - All Warriors in the Cave should be assigned to group "attack" (to actually attack the Dragon).
  - Farmers in the Cave should be moved back to the Village (group "village") since Farmers should stay in the Village.
- This plan ensures:
  - Warriors end up in the Cave and attack the Dragon.
  - Farmers remain in the Village, with potential to spawn more villagers.
  - Spawned villagers help increase DPS over time.
  - Early attack is guaranteed by sending Warriors to attack in the Cave stage.
  - The Cave will repeatedly contain a substantial share of Warriors (as Warriors are always moved to the Cave on village-to-cave transition and then attack).

Python implementation

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Split villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Strategy: All Warriors should go to the Cave (to attack later)
        for w in warriors:
            environment.assign_group(w, "cave")

        # Farmers should stay in Village by default, but we can spawn new villagers
        # Determine how many spawns we can attempt this step
        avail_farmers = len(farmers)

        # Wheat available for spawning
        wheat = getattr(environment.farm, "wheat", 0)

        # Max possible spawns based on wheat
        max_farm_spawns = wheat // 10
        max_warrior_spawns = (wheat // 12)

        # First, cap spawns by the number of farmers available
        s_farm = min(avail_farmers // 2, max_farm_spawns)

        # Wheat left after farmer-spawns
        wheat_left = wheat - 10 * s_farm
        remaining_farmers_after_farm = avail_farmers - 2 * s_farm

        # Warrior-spawns are limited by remaining farmers and remaining wheat
        s_warrior = min(remaining_farmers_after_farm // 2, wheat_left // 12)

        # Slight early-game boost to ensure some spawns happen in the first 10 steps
        if step <= 10:
            # If we can spawn one more farmer and still have enough farmers and wheat, try it
            if avail_farmers >= 2 and wheat >= 10 and s_farm < avail_farmers // 2:
                s_farm += 1
                wheat_left -= 10

            # Try to spawn one more warrior if possible
            if remaining_farmers_after_farm >= 2 and wheat_left >= 12:
                s_warrior += 1
                wheat_left -= 12

        # Recompute final allocation counts (ensuring non-negative)
        s_farm = max(0, s_farm)
        s_warrior = max(0, s_warrior)

        # Assign specific farmers to groups
        # First 2*s_farm farmers go to "spawn farmer"
        farmers_to_spawn_farm = farmers[: 2 * s_farm]
        # Next 2*s_warrior farmers go to "spawn warrior"
        start_warrior = 2 * s_farm
        farmers_to_spawn_warrior = farmers[start_warrior: start_warrior + 2 * s_warrior]
        # The rest stay in the farm (Village)
        farmers_to_farm = farmers[start_warrior + 2 * s_warrior:]

        for f in farmers_to_spawn_farm:
            environment.assign_group(f, "spawn farmer")
        for f in farmers_to_spawn_warrior:
            environment.assign_group(f, "spawn warrior")
        for f in farmers_to_farm:
            environment.assign_group(f, "farm")

        # Note: Warriors have already been moved to the cave above.
        # There is no need to assign any farmers to stay in village explicitly here beyond "farm"/spawn groups.

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave, decide who attacks and who stays
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                # Warriors should attack the Dragon
                environment.assign_group(c, "attack")
            else:
                # Farmers should go back to the Village
                environment.assign_group(c, "village")
```