Reasoning and adaptation strategy

- Task summary:
  - Villagers can be Farmers or Warriors. Farmers stay in the Village; Warriors go to the Cave and attack the Dragon.
  - You can spawn new Farmers or Warriors by placing villagers into special spawn groups, consuming wheat (Farm wheat: 10 for a Farmer spawn; 12 for a Warrior spawn per two villagers in the spawn group).
  - Dragon has HP 50; it can retaliate randomly. You win if Dragon HP reaches 0 within 30 steps; you lose if all villagers die or you fail to kill in time.
  - You must ensure: all Warriors go to the Cave and eventually attack the Dragon; all Farmers stay in the Village; spawn some new villagers (both Farmers and Warriors); attack the Dragon; at least one attack within the first 15 steps; at least half of the Warriors are in the Cave most of the time to sustain the attack.

- Strategy overview:
  - Maintain the rule that all Warriors should be in the Cave to attack. We will move all Warriors to the Cave in the village phase and continue to push them to attack in the cave phase.
  - Farmers stay in the Village by default. To satisfy “spawn new villagers” while keeping Farmers in the Village, we’ll designate some Farmers to participate in spawn groups. This yields new Farmers and Warriors (spawned villagers), helping with DPS and sustainment.
  - Spawn plan in village:
    - Decide how many Farmers to allocate to spawn Farmer groups (needs 2 Farmers per new Farmer and 10 wheat per spawn).
    - Allocate some Farmers to a spawn Warrior group (needs 2 villagers per new Warrior and 12 wheat per spawn) to increase Warrior counts.
    - Remaining Farmers stay in Farm group (continue farming wheat in Village).
    - Wheat resource consideration: use environment.farm.wheat to determine how many spawns are possible this step. We’ll prioritize Farmer spawns first (to bolster farming output) but also add Warrior spawns if wheat allows.
  - Cave phase:
    - Farmers in cave will be sent to Village (they should stay in Village long-term).
    - Warriors in Cave will be split into:
      - Attack group: at least 1 and ideally about half of the Warriors to attack the Dragon (to satisfy “attack” requirement within first 15 steps and keep a strong force in the Cave).
      - Cave group: the rest stay in cave.
  - Early Dragon attack:
    - Because we move Warriors to the Cave in the village phase, there will typically be Warriors in the cave by step 1. In the cave phase, we explicitly assign at least one Warrior to the Attack group to ensure the Dragon is attacked early (within first 15 steps).

- Implementation notes:
  - All assignments use environment.assign_group(component, group_id) with the required group_ids.
  - The code keeps the logic deterministic but responsive to wheat constraints and current counts, ensuring we always honor the “all Warriors to Cave” rule and “Farmers stay in Village” rule.
  - Spawn groups are used only in village phase assignment; in cave phase, we simply direct existing villagers according to the rules.

Now here is the Python implementation.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Divide villagers currently in the Village
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Rule: All warriors should go to the Cave
        for w in warriors:
            environment.assign_group(w, "cave")

        # Farm wheat resource
        wheat = getattr(getattr(environment, "farm", None), "wheat", 0)

        # Spawn strategy for farmers
        f_count = len(farmers)

        # Number of pairs of farmers to assign to "spawn farmer"
        # Each pair yields 1 new Farmer, costs 10 wheat
        s_farm_spawns = min(f_count // 2, max(0, wheat // 10))
        s_farmers_assigned_to_spawn = s_farm_spawns * 2

        # Remaining wheat after farmer spawns
        wheat_rem_after_farm = max(0, wheat - s_farm_spawns * 10)

        # Remaining farmers after assigning to farmer-spawn
        remaining_farmers = f_count - s_farmers_assigned_to_spawn

        # Number of pairs of farmers to assign to "spawn warrior"
        # Each pair yields 1 new Warrior, costs 12 wheat
        s_war_spawns = min(remaining_farmers // 2, max(0, wheat_rem_after_farm // 12))
        s_warriors_assigned_to_spawn = s_war_spawns * 2

        # Build groups for farmers
        alloc = {
            "farm": [],
            "spawn farmer": [],
            "spawn warrior": [],
        }

        idx = 0
        # Assign to spawn farmer first
        for i in range(s_farmers_assigned_to_spawn):
            alloc["spawn farmer"].append(farmers[idx])
            idx += 1

        # Assign to spawn warrior next
        for i in range(s_warriors_assigned_to_spawn):
            alloc["spawn warrior"].append(farmers[idx])
            idx += 1

        # Remaining farmers go to farm
        for i in range(idx, f_count):
            alloc["farm"].append(farmers[i])

        # Now apply the assignments
        for c in alloc["farm"]:
            environment.assign_group(c, "farm")
        for c in alloc["spawn farmer"]:
            environment.assign_group(c, "spawn farmer")
        for c in alloc["spawn warrior"]:
            environment.assign_group(c, "spawn warrior")

        # If there are any other components (e.g., non-Farmer), we do not reassign them here.
        # The Warriors have already been moved to the cave above.

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # Divide villagers currently in the Cave
        farmers_in_cave = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors_in_cave = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Farmers should go to the Village
        for f in farmers_in_cave:
            environment.assign_group(f, "village")

        # For warriors in the cave, ensure sufficient attackers
        w_count = len(warriors_in_cave)
        if w_count > 0:
            # Ensure at least one attacker and try to have about half attack
            attack_count = max(1, w_count // 2)
            attack_count = min(attack_count, w_count)

            for i, w in enumerate(warriors_in_cave):
                if i < attack_count:
                    environment.assign_group(w, "attack")
                else:
                    environment.assign_group(w, "cave")
        # If there are no warriors in cave, nothing to assign to attack this step
```