

## Analysis and v7 Strategy

After studying the simulation results (v1: 21.3, v4: 20.0, v6: 21.3), I identified that the key tradeoff is **warrior DPS vs survival from dragon counter-attacks**:

- v6 (attack until scm=6): More DPS per cycle BUT 2HP starvation loss/cycle + dragon counter → warriors die fast → coverage gaps
- v4 (attack until scm=4, leave at scm=5): 4 attacks per 7-step cycle, only 1HP starvation → warriors survive ~16 steps → consistent coverage

**v7 improvements over v4 (20.0 steps):**
1. **Warriors used for spawning instead of farmers**: A warrior spawning costs 2W farming; a farmer spawning costs 5W farming. Keep all farmers farming!
2. **Tighter early spawning**: Build wheat for 2 steps, spawn warrior at step 2, then spawn every 2-3 steps
3. **Warriors go to cave immediately after eating** (scm=0 or 1 → cave) for maximum 4-attack cycles
4. **No endgame farmer cave rush** until HP ≤ 6 (keeps wheat production for warrior pipeline)
5. **Simplify meal logic**: eat at scm≥4 (gives warriors a full 4-attack cycle after returning fresh)

```py
from