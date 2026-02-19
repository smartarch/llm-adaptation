# FCL constraints examples for Dragon Hunt

In the examples below, the following sets represent the system's components: $\mathit{Dragons}$, $\mathit{Villagers}$; and ensembles: $\mathit{Farm}$, $\mathit{GoToCave}$, $\mathit{SpawnFarmer}$, $\mathit{SpawnWarrior}$, $\mathit{Attack}$, $\mathit{StayInCave}$, $\mathit{GoToVillage}$.

## The game is won

The game is won when the Dragon is killed, i.e., when its health points reach zero. The set $\mathit{Dragons}$ contains all components of type `Dragon` (only one in this case). We use the $\lozenge^n_t$ operator to express that the Dragon's health reaches zero at some point of the game (technically, at least once).
$$\forall d \in \mathit{Dragons}: \lozenge^1_{\mathit{MAX}}\ d.hp \le 0$$

## The Dragon is attacked at least once within the first 15 steps of the game

To express that the Dragon is attacked at least once during the first 15 steps of the run of the system, we check that the `Attack` ensemble has at least one member (its cardinality is $\ge 1$).
$$\lozenge^1_{15} |\mathit{Attack}| \ge 1$$

## All farmers should stay in the Village

Our strategy desires that all farmers stay in the village. First, we define a set of all farmers by selecting some of the `Villager` components based on their role.
$$\mathit{Farmers} = \{ v \in \mathit{Villagers} \mid \mathit{v.role} = \text{``Farmer''} \}$$

Then, we use $\lozenge^{\mathit{MAX}}_{\mathit{MAX}}$ to express that it should always hold (in every time step) that the farmer's location is the village.
$$\forall f \in \mathit{Farmers}: \lozenge^{\mathit{MAX}}_{\mathit{MAX}}\ \mathit{f.location} = \text{``Village''}$$

## All warriors should go to the Cave

Each warrior should be in the `GoToCave` ensemble (i.e., go from the Village to the Cave) at least once.

$$\mathit{Warriors} = \{ v \in \mathit{Villagers} \mid \mathit{v.role} = \text{``Warrior''} \}$$
$$\forall w \in \mathit{Warriors}: \lozenge^{1}_\mathit{MAX}\ w \in \mathit{GoToCave}$$

## Spawn at least a few new warriors

To effectively kill the dragon, we want at least three warriors to be spawned during the run of the system. The rules of the game define that two villagers are necessary to spawn a new one. The `SpawnWarrior` ensemble should therefore have at least two members at least three times.
$$\lozenge^3_{\mathit{MAX}} |\mathit{SpawnWarrior}| \ge 2$$

## Spawn at least a few new farmers

(similar to above)

$$\lozenge^3_{\mathit{MAX}} |\mathit{SpawnFarmer}| \ge 2$$

## After a villager gets to the cave, it should attack the dragon

An implication can be used to express a sequence of actions. If a component is a member of the `GoToCave` ensemble, it moves from the Village to the Cave. We want such components to attack the Dragon at some point in the future (i.e., at least once be a member of the `Attack` ensemble).
$$\forall v \in \mathit{Villagers}: v \in \mathit{GoToCave} \implies \lozenge^1_\mathit{MAX}\ v \in \mathit{Attack}$$
However, it can happen that a villager moves to the Cave in the last step of the trace, which leaves no more steps for them to attack the Dragon, leading to constraint violation. To prevent this, we update the implication to not enforce it in the last step (i.e., when $\mathit{MAX} = 0$).
$$\left(v \in \mathit{GoToCave} \wedge \mathit{MAX}>0 \right) \implies \lozenge^1_\mathit{MAX}\ v \in \mathit{Attack}$$

## Warriors should be mostly in the cave

We also want the warriors to spend most of the time in the Cave, but the fact that they are spawned in the Village and first need to go to the cave prevents us from using the "always" operator ($\lozenge^{\mathit{MAX}}_{\mathit{MAX}}$). We thus formulate the constraint as follows: at least 80% of the time (i.e., $0.8$ times the number of remaining steps), at least half of the warriors are in the Cave.

$$\mathit{Warriors} = \{ v \in \mathit{Villagers} \mid \mathit{v.role} = \text{``Warrior''} \}$$
$$\mathit{InCave} = \{ v \in \mathit{Villagers} \mid \mathit{v.location} = \text{``Cave''} \}$$
$$\lozenge^{0.8 \cdot \mathit{MAX}}_\mathit{MAX} |\mathit{Warriors} \cap \mathit{InCave}| \ge 0.5 \cdot |\mathit{Warriors}|$$

## Spawn a new warrior every 10 steps

To express this constraint, we reformulate it as follows. If no warrior was spawned in the previous 10 steps, spawn a warrior. We use $t=-10$ and $n=10$ to express that the `SpawnWarrior` ensemble had less than 2 members in each of the previous 10 steps.
$$\lozenge^{10}_{-10} |\mathit{SpawnWarrior}| < 2 \implies |\mathit{SpawnWarrior}| \ge 2$$
