Strategy reasoning and approach

Goal-driven reasoning:
- Warriors are the primary dps, so they should be the ones actively engaging the Dragon. Rule: all warriors must go to the Cave and then attack the Dragon.
- Farmers stay in the Village. They should handle farming (to generate wheat) and also contribute to population growth by spawning new villagers when resources allow.
- Spawning helps ensure we can field enough fighters quickly. There are two spawn routes:
  - spawn farmer: for every 2 villagers assigned to this group and 10 wheat, a new Farmer is spawned.
  - spawn warrior: for every 2 villagers assigned to this group and 12 wheat, a new Warrior is spawned.
  We implement spawning by allocating a small number of farmers to the spawn groups when wheat is available. The engine will spawn new villagers accordingly.
- Early attack requirement: The Dragon must be attacked at least once within the first 15 steps. To guarantee this, we:
  - Move all existing Warriors to the Cave to prepare for attack.
  - If there are no Warriors yet and step <= 15, and we have at least two Farmers with enough wheat, we spawn at least one Warrior by assigning two Farmers to the spawn warrior group (needs 12 wheat). This ensures that a Warrior can attack by the time they arrive.
- Cost and resource awareness: We use environment.farm.wheat to decide whether we can afford spawning actions (10 wheat for spawning a Farmer, 12 wheat for spawning a Warrior). We also avoid over-spawning; we spawn at most a couple of villagers per step to keep wheat balance and avoid stalling.

High-level behavior:
- assign_in_village:
  - If there are no Warriors yet and we’re within the first 15 steps and have enough Farmers and wheat, allocate 2 Farmers to spawn warrior (to ensure early attack) and put the rest to farming; otherwise, move Warriors to cave and mix Farmers between farming and spawning farmers (and possibly a warrior spawn if wheat is enough and there are at least 2 Farmers).
  - Always try to keep some Farmers in a spawning position if wheat allows, to gradually increase population, while ensuring Farmers mostly farm.
- assign_in_cave:
  - All Warriors in the Cave move to the attack group (attack the Dragon).
  - All Farmers in the Cave return to the Village (village group) to resume farming/spawn activities.

Code implementation

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate villagers by role
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # Helper to assign a single component
        def assign(c, grp):
            environment.assign_group(c, grp)

        # 1) If no warriors yet and we are in the first 15 steps, try to spawn a Warrior
        if len(warriors) == 0 and step <= 15 and len(farmers) >= 2:
            # Need at least 12 wheat to spawn a Warrior (with 2 farmers in group)
            if environment.farm.wheat >= 12:
                # Put two farmers into the spawn warrior group to trigger a spawn
                assign(farmers[0], "spawn warrior")
                assign(farmers[1], "spawn warrior")
                # The rest of farmers go to farming
                for c in farmers[2:]:
                    assign(c, "farm")
                # All existing farmers accounted for; done for this step
                # Warriors (none currently) would be handled by later steps
                return
            else:
                # Not enough wheat yet; fall back to normal distribution
                for f in farmers:
                    assign(f, "farm")
                for w in warriors:
                    assign(w, "cave")
                return

        # 2) Normal path: move all existing Warriors to the Cave (to prep for attack)
        for w in warriors:
            assign(w, "cave")

        # 3) Farmers: decide to spawn farmers if wheat allows; otherwise farm
        if len(farmers) >= 2 and environment.farm.wheat >= 10:
            # Spawn up to 2 farmers this step if possible (requires 10 wheat)
            to_spawn_farmers = min(2, len(farmers))
            # Put first few to spawn farmer
            for f in farmers[:to_spawn_farmers]:
                assign(f, "spawn farmer")
            # The rest (if any) go to farming
            for f in farmers[to_spawn_farmers:]:
                assign(f, "farm")
        else:
            # Nothing to spawn or not enough wheat, all farmers farm
            for f in farmers:
                assign(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the cave, all Warriors should attack; Farmers should go back to Village
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```