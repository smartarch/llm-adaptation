Reasoning and strategy

- Task understanding:
  - We must split villagers into groups depending on their current role and where they are (village or cave).
  - Warriors should always be sent to the cave to attack the dragon. Farmers should remain in the village to farm and/or spawn new villagers.
  - Spawning works via two special groups in the village:
    - "spawn farmer": for every two villagers in this group and 10 wheat, a new Farmer is spawned.
    - "spawn warrior": for every two villagers in this group and 12 wheat, a new Warrior is spawned.
  - All villagers must be assigned to exactly one group each step, and we should explicitly re-assign them to the chosen group every step.
  - In the cave, we should reassign Farmers back to the village (to farm or spawn) and Warriors to the "attack" action (to be in position to attack the Dragon).

- Adaptation strategy (design goals):
  - Primary combat objective: Move all Warriors to the cave to attack the Dragon as soon as possible (via the cave step -> attack step).
  - For Farmers, maximize wheat production to enable spawning and to fuel future reinforcements:
    - Use a simple, deterministic split:
      - If there are at least two Farmers and there is enough wheat, designate up to two Farmers to the "spawn farmer" group (to potentially spawn new Farmers).
      - If there is enough wheat and at least four Farmers total, designate two additional Farmers to the "spawn warrior" group (to spawn additional Warriors later on).
      - The remaining Farmers stay in the "farm" group to keep wheat production high.
    - If there are not enough Farmers or wheat, farmers mostly stay in "farm".
  - In the cave:
    - Reassign Warriors to "attack".
    - Reassign Farmers to "village" to continue farming or spawning; this ensures Farmers stay out of the cave as per the strategy constraints.

- What changes this strategy makes:
  - Enforces the requirement that all Warriors go to the cave (to attack) and all Farmers stay in the Village (to farm/spawn).
  - Introduces a small, conservative spawning plan to gradually increase population when resources allow, without risking starving farming needs prematurely.
  - Keeps the solution simple and deterministic for reproducibility.

Python code

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Divide villagers in the Village into:
        - "farm": stay in Village and farm
        - "cave": go to the Cave (this is allowed by the strategy, though in our design
                  we primarily use this for Warriors; Farmers are kept in Village)
        - "spawn farmer": for every two villagers in this group and 10 wheat, a new Farmer is spawned
        - "spawn warrior": for every two villagers in this group and 12 wheat, a new Warrior is spawned

        All Warriors should end up in the cave in this step (via the cave function),
        and all Farmers should stay in the Village or be placed in the spawning groups
        as described below.
        """
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Wheat available for spawning decisions
        wheat = getattr(getattr(environment, "farm", None), "wheat", 0)

        # Decide spawn allocations (conservative, deterministic)
        spawn_farmers = 0
        spawn_warriors = 0

        # Only consider spawning if we have at least 2 farmers to allocate to spawn groups
        if len(farmers) >= 2 and wheat >= 12:
            # Up to 2 can be allocated to "spawn farmer"
            spawn_farmers = min(2, len(farmers))

            # If wheat is sufficient and we have at least 4 farmers, allocate up to 2 to "spawn warrior"
            if wheat >= 24 and len(farmers) >= 4:
                spawn_warriors = min(2, len(farmers) - spawn_farmers)

        # Remaining farmers will go to "farm"
        # Now assign groups for farmers in a deterministic order
        # First, assign to spawn farmer
        idx = 0
        for i, f in enumerate(farmers):
            if i < spawn_farmers:
                environment.assign_group(f, "spawn farmer")
            elif i < spawn_farmers + spawn_warriors:
                environment.assign_group(f, "spawn warrior")
            else:
                environment.assign_group(f, "farm")

        # Assign all Warriors to cave (they will attack from cave in the cave step)
        for w in warriors:
            environment.assign_group(w, "cave")

        # Farmers not in the spawn groups are already assigned to "farm".
        # If there are any farmers not yet assigned due to zero wheat or small numbers,
        # ensure they are assigned to "farm" (safe default).
        if len(farmers) > 0:
            for i in range(len(farmers)):
                f = farmers[i]
                # If not already assigned (safety check)
                # We assume environment.assign_group can be idempotent; to be safe, re-assign
                if i >= spawn_farmers + spawn_warriors:
                    environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Divide villagers in the Cave into:
        - "attack": Attack the Dragon
        - "cave": Stay in the Cave
        - "village": Go to the Village

        Strategy:
        - All Warriors should go to "attack" to fight the Dragon.
        - All Farmers should go to "village" to farm or spawn new villagers.
        - We avoid keeping Farmers in the Cave, per the strategy description.
        """
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Assign Warriors to attack
        for w in warriors:
            environment.assign_group(w, "attack")

        # Assign Farmers to go back to Village
        for f in farmers:
            environment.assign_group(f, "village")

        # If any other components exist (shouldn't per provided attributes), assign to cave as safe default
        # (This is a guard against unexpected component types.)
        others = [c for c in components if c not in farmers and c not in warriors]
        for o in others:
            environment.assign_group(o, "cave")
```