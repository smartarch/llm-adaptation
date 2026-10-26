## Analysis of the previous attempt

The likely cause of the 0% win rate is the Dragon's counterattack, not the group split. Each attack round, every villager in the Cave has a 40% chance of taking 1 damage, and there is a 20% chance of losing one villager. Killing a 50 HP Dragon with a steady trickle of 1 to 2 warriors takes about 17 warrior-attacks spread over many rounds. Over that many rounds, each warrior takes roughly 6 or more damage on average, so most of the army dies before the Dragon does.

The fix is to minimise the number of rounds, not just the total number of attacks. Damage per round scales with the number of warriors attacking at once, so the Dragon should be hit by a large group in a few rounds.

Examples:
- 1 to 2 warriors: about 9 rounds, heavy losses.
- 5 warriors: 15 damage per round, about 4 rounds.
- 6 warriors: 18 damage per round, about 3 rounds.

## Revised strategy: wait in the Cave, then strike together

- **Farmers** never leave the Village. Two always stay on `"farm"`. The rest are paired and converted into warriors (`"spawn warrior"`, 12 wheat per pair). If the farmer count drops below 4, a pair is spawned as a farmer instead (10 wheat).
- **Warriors** move to `"cave"` immediately, but they only wait there. Waiting in the Cave costs nothing, because the Dragon only counterattacks when it is attacked.
- **Strike:** once at least 5 warriors are in the Cave, or step 12 is reached (to meet the first-15-steps requirement), the strike begins. This is a one-way switch. From then on, all warriors in the Cave attack every step, and any warrior that arrives later joins the attack immediately.

This keeps every requirement: all warriors go to the Cave, they attack soon after arriving and within the first 15 steps, farmers stay in the Village, and both roles are spawned.

```py
import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Batch-strike strategy.
    - Farmers never leave the Village; two always farm, the rest spawn
      warriors (pairs, 12 wheat) and farmers if the farmer count gets low.
    - Warriors move to the Cave immediately and wait there (no attacks yet).
    - Once >=5 warriors are in the Cave, or step >= 12, the strike starts:
      all warriors in the Cave attack every step. Late arrivals join at once.
      A large group kills the Dragon in few rounds, so each warrior faces
      far fewer counterattacks.
    """

    WARRIOR_SPAWN_COST = 12
    FARMER_SPAWN_COST = 10
    MIN_FARMING = 2
    MIN_FARMERS = 4
    STRIKE_WARRIORS = 5
    STRIKE_STEP = 12

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.strike = False

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat

        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        # Warriors always head to the Cave (they wait there until the strike).
        for w in warriors:
            environment.assign_group(w, "cave")

        # Keep a minimal farming core.
        reserve = min(self.MIN_FARMING, len(farmers))
        farming = farmers[:reserve]
        available = farmers[reserve:]

        spawn_warrior = []
        spawn_farmer = []

        # Rebuild the farmer economy if too few farmers remain.
        if len(farmers) < self.MIN_FARMERS:
            while len(available) >= 2 and wheat >= self.FARMER_SPAWN_COST:
                spawn_farmer.extend(available[:2])
                available = available[2:]
                wheat -= self.FARMER_SPAWN_COST

        # Convert the remaining farmers into warriors while wheat allows.
        while len(available) >= 2 and wheat >= self.WARRIOR_SPAWN_COST:
            spawn_warrior.extend(available[:2])
            available = available[2:]
            wheat -= self.WARRIOR_SPAWN_COST

        # Anyone left over keeps farming.
        farming.extend(available)

        for f in spawn_farmer:
            environment.assign_group(f, "spawn farmer")
        for f in spawn_warrior:
            environment.assign_group(f, "spawn warrior")
        for f in farming:
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        warriors_in_cave = [c for c in components if c.role == "Warrior"]

        # One-way switch: start the strike once enough warriors are gathered
        # or the time limit for the first attack is reached.
        if not self.strike and (len(warriors_in_cave) >= self.STRIKE_WARRIORS
                                or step >= self.STRIKE_STEP):
            self.strike = True

        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack" if self.strike else "cave")
            else:
                # Farmers never fight; send them back to the Village.
                environment.assign_group(c, "village")
```