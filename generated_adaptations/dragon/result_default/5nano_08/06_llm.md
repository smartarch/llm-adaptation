Reasoning and improved adaptation strategy

Root idea:
- Warriors are the primary DPS in the cave, so getting them to the Dragon as early as possible is crucial to reduce overall time to kill.
- Farmers are the wheat engines. They should still help the economy, but in the very early game we prefer to push Warriors into the cave first and use Farmers for spawning as soon as we have enough wheat.
- To balance early aggression with growth, we adopt a two-phase spawn policy:
  - In the first several steps (step < 12), spawn Warriors as much as possible given current wheat and available Farmers. This accelerates early DPS.
  - After that threshold, switch back to the previous balanced approach: spawn Farmers first (to grow wheat), then spawn Warriors if resources allow.
- Warriors will always be sent to the Cave; Farmers stay in Village to farm or spawn. Spawning rules and wheat checks remain the same, but the order of evaluation changes to favor early combat power.

What changes I made:
- In assign_in_village, introduce a step-based spawn order switch:
  - If step < 12: allocate as many “spawn warrior” groups as possible first, then allocate “spawn farmer” groups, then remaining Farmers to farming.
  - Else: fall back to the earlier approach (farm spawns first, then warrior spawns, then remaining farmers farm).
- All Warriors are still moved to the Cave, and Farmers are assigned to either farming, spawning, or returning to the Village as appropriate.

Python code

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate villagers by role
        farmers = [c for c in components if getattr(c, 'role', None) == 'Farmer']
        warriors = [c for c in components if getattr(c, 'role', None) == 'Warrior']

        # 1) All Warriors go to the Cave (to attack)
        for w in warriors:
            environment.assign_group(w, "cave")

        # 2) Spawn strategy based on step
        initial_wheat = getattr(getattr(environment, 'farm', None), 'wheat', 0)

        if step < 12:
            # Early game: prioritize spawning Warriors first
            max_war_spawns = min(initial_wheat // 12, len(farmers) // 2)
            if max_war_spawns > 0:
                to_spawn_war = farmers[:2 * max_war_spawns]
                for c in to_spawn_war:
                    environment.assign_group(c, "spawn warrior")

            remaining_farmers = farmers[2 * max_war_spawns:]
            wheat_after_war_spawns = initial_wheat - max_war_spawns * 12

            # Then spawn Farmers with remaining wheat
            max_farm_spawns = min(wheat_after_war_spawns // 10, len(remaining_farmers) // 2)
            if max_farm_spawns > 0:
                to_spawn_farm = remaining_farmers[:2 * max_farm_spawns]
                for c in to_spawn_farm:
                    environment.assign_group(c, "spawn farmer")

            remaining_after_spawns = remaining_farmers[2 * max_farm_spawns:]
            for c in remaining_after_spawns:
                environment.assign_group(c, "farm")
        else:
            # Later game: fall back to balanced approach
            max_farm_spawns = min(initial_wheat // 10, len(farmers) // 2)
            if max_farm_spawns > 0:
                to_spawn_farm = farmers[:2 * max_farm_spawns]
                for c in to_spawn_farm:
                    environment.assign_group(c, "spawn farmer")

            remaining_farmers2 = farmers[2 * max_farm_spawns:]
            wheat_after_farm = initial_wheat - max_farm_spawns * 10

            max_war_spawns = min(wheat_after_farm // 12, len(remaining_farmers2) // 2)
            if max_war_spawns > 0:
                to_spawn_war = remaining_farmers2[:2 * max_war_spawns]
                for c in to_spawn_war:
                    environment.assign_group(c, "spawn warrior")

            remaining_after_war = remaining_farmers2[2 * max_war_spawns:]
            for c in remaining_after_war:
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In Cave: Warriors attack, Farmers go back to Village
        for c in components:
            if getattr(c, 'role', None) == 'Warrior':
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```