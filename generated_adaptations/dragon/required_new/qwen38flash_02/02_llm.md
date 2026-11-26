

Looking at this game, I need to design a strategy that balances food production, villager spawning, and continuous dragon attacks within 30 steps while managing the eating constraint.

**Strategy Analysis:**

Key observations:
- Dragon has 100 HP, regenerates 5 HP/step when not attacked → must attack EVERY step to avoid regen
- Warriors deal 3 damage, Farmers deal 1 → Warriors are 3x more efficient
- A villager can stay in cave for max ~3 steps (travel + cave + travel back ≤ 5 steps without eating)
- Must maintain continuous attacks → need rotation of warriors (send new wave while old wave returns to eat)
- Food economy: Farmers produce 5 wheat/step, need ~1 wheat per villager per 6 steps for eating

**Adaptation Strategy:**

1. **Village Phase (early):** Farm aggressively to build wheat. Spawn warriors as soon as wheat allows.
2. **Rotation System:** Send warriors to cave in waves. Warriors with steps_since_meal ≤ 2 go to cave. Warriors in cave attack for 2-3 steps, then return.
3. **Eating Priority:** Villagers with steps_since_meal ≥ 4 must eat immediately. Those with ≥ 3 should eat rather than risk travel.
4. **Attack Priority:** In cave, everyone attacks unless about to starve or nearly dead.
5. **Late Game:** If dragon HP is low, throw everyone in (sacrifice if needed).

```py
import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step):
        # Separate components by role
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]
        
        wheat = environment.farm.wheat
        dragon_hp = environment.dragon.hp
        
        # Count how many warriors are currently in cave (from observation)
        warriors_in_cave = sum(1 for w in environment.warriors if w.location == "Cave")
        farmers_in_cave = sum(1 for f in environment.farmers if f.location == "Cave")
        total_warriors = len(environment.warriors)
        total_villagers = len(environment.warriors) + len(environment.farmers)
        
        # Phase 1: Handle critical eating (steps_since_meal >= 5 means they'll starve next step)
        assigned = set()
        
        # Force eat for those who are critically hungry
        for v in components:
            if v.steps_since_meal >= 5 and wheat >= 1:
                environment.assign_group(v, "eat")
                assigned.add(id(v))
                wheat -= 1  # Track consumed wheat (approximate)
        
        # Phase 2: Handle urgent eating (steps_since_meal >= 3, should eat now to be safe)
        for v in components:
            if id(v) in assigned:
                continue
            if v.steps_since_meal >= 3 and wheat >= 1:
                environment.assign_group(v, "eat")
                assigned.add(id(v))
                wheat -= 1
        
        # Phase 3: Send warriors to cave if they can handle the trip
        # They can go if steps_since_meal <= 2 (will be at 3,4,5 max in cave then return)
        remaining_warriors = [w for w in warriors if id(w) not in assigned]
        
        # We want at least 3-4 warriors attacking at a time for good DPS
        target_in_cave = min(5, total_warriors)
        warriors_to_send = max(0, target_in_cave - warriors_in_cave)
        
        # If dragon is low HP, send everyone possible
        if dragon_hp <= 15:
            warriors_to_send = len(remaining_warriors)
        
        sent_to_cave = 0
        for w in remaining_warriors:
            if sent_to_cave >= warriors_to_send:
                break
            if w.steps_since_meal <= 1 and w.hp >= 2:
                environment.assign_group(w, "cave")
                assigned.add(id(w))
                sent_to_cave += 1
        
        # Phase 4: Spawn warriors if beneficial and affordable
        # Need: 2 villagers in spawn group + 12 wheat
        # Only spawn if we have enough farmers to spare and enough wheat
        remaining_components = [c for c in components if id(c) not in assigned]
        remaining_farmers = [c for c in remaining_components if c.role == "Farmer"]
        
        # Check if we should spawn a warrior
        actual_wheat = environment.farm.wheat
        # Only spawn if we have surplus wheat and enough villagers
        can_spawn_warrior = (actual_wheat >= 12 and len(remaining_components) >= 2)
        # Also ensure we have enough eating/farming capacity
        can_afford_food = (actual_wheat - 12) >= len(environment.warriors) + len(environment.farmers)
        
        if can_spawn_warrior and can_afford_food and dragon_hp > 20:
            # Use 2 farmers for spawning
            spawn_candidates = [f for f in remaining_components if f.role == "Farmer" and id(f) not in assigned]
            if len(spawn_candidates) >= 2:
                environment.assign_group(spawn_candidates[0], "spawn warrior")
                assigned.add(id(spawn_candidates[0]))
                environment.assign_group(spawn_candidates[1], "spawn warrior")
                assigned.add(id(spawn_candidates[1]))
        
        # Phase 5: Farm remaining villagers
        # Priority: farmers farm (5 wheat), warriors farm (2 wheat) if not going to cave
        for c in remaining_components:
            if id(c) in assigned:
                continue
            if c.steps_since_meal <= 2:
                environment.assign_group(c, "farm")
                assigned.add(id(c))
            else:
                # Moderate hunger - eat if possible
                if wheat >= 1:
                    environment.assign_group(c, "eat")
                else:
                    environment.assign_group(c, "farm")
                assigned.add(id(c))
        
        # Safety: ensure all are assigned
        for c in components:
            if id(c) not in assigned:
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        dragon_hp = environment.dragon.hp
        
        # In cave: priority is to attack, but return if about to starve or dying
        assigned = set()
        
        for c in components:
            if id(c) in assigned:
                continue
            
            # Must return if critically hungry (will starve in 1-2 steps)
            if c.steps_since_meal >= 4:
                environment.assign_group(c, "village")
                assigned.add(id(c))
                continue
            
            # Return if very low HP and not critical to kill
            if c.hp <= 1 and dragon_hp > 10:
                environment.assign_group(c, "village")
                assigned.add(id(c))
                continue
            
            # Return if moderate hunger and we have enough attackers
            if c.steps_since_meal >= 3 and dragon_hp > 15:
                environment.assign_group(c, "village")
                assigned.add(id(c))
                continue
            
            # Otherwise, attack!
            environment.assign_group(c, "attack")
            assigned.add(id(c))
        
        # Safety: ensure all are assigned
        for c in components:
            if id(c) not in assigned:
                environment.assign_group(c, "attack")
```