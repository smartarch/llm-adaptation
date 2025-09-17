# User constraints

## Semantics

* $\square \phi$ means that $\phi$ holds in each step (always)
* $\lozenge \phi$ means that $\phi$ holds at least once
* $\lozenge^n \phi$ means that $\phi$ holds at least $n$ tímes
* $\lozenge^{p\%} \phi$ means that $\phi$ holds at least $p\%$ of the time
* $\lozenge_t \phi$ means that $\phi$ holds at least once within the next $t$ steps or the simulation ends in less than $t$ steps

* $step$ is the current step of the simulation, $-step$ is the number of steps remaining until the end of the simulation (e.g., $-1$ means the last step)
* CAPITALIZED are constants
* lower_case are name of ensembles and sets of components, e.g.
  * $attack$ is the attack ensemble
  * $protecting(f)$ is the protecting ensemble for field $f$
  * $fields$ is the set of all fields (i.e., components of type Field)

## Examples

### Each field is not overprotected.

= in each step (always), number of drones assigned to protect field (size of "protecting" ensemble) is not bigger than number of drones for full protection

$\forall f \in fields: \square |protecting(f)| \le f.drones\_for\_full\_protection$

### The dragon is attacked at least once.

= at least once, the attack ensemble has at least one member

$\lozenge |attack| >= 1$

### The most threatened field is fully protected.

= in each step (always), the ensemble corresponding to the field with the highest threat level has at least as many drones as are required for full protection of the field

$\square |protecting(max\_threatened\_field)| \ge max\_threatened\_field.drones\_for\_full\_protection$

### If the threat level is at least 0.2 for 10 consecutive time steps, the field is fully protected

= for each field, if its threat level is at least 0.2, the field should be fully protected (as many drones assigned to the corresponding ensemble) within 10 time steps, unless the threat level drops below 0.2 during that time

$\forall f \in fields: f.threat\_level \ge 0.2 \implies \lozenge_{10} \left( |protecting(f)| >= f.drones\_for\_full\_protection \vee f.treat\_level < 0.2 \right)$

### The dragon should be attacked within the first 10 steps of the game.

- Or within 10 steps after it appears (currently, the dragon exists from start)

$\lozenge_{10} |attack| \ge 1$

### After a warrior gets to the cave, it should attack the dragon (at any time in the future).

= After a warrior is in the "cave" ensemble (=he moves to the cave), they should be in the "attack" ensemble (=attack the dragon) before the game ends.

* unless it is in the “cave” ensemble in the last step of the game

$\forall w \in warriors: w \in cave \wedge \neg step = -1 \implies \lozenge w \in attack$

### After a warrior gets to the cave, it should attack the dragon within 5 time steps.

= After a warrior is in the “cave” ensemble (=he moves to the cave), they should be in the “attack” ensemble (=attack the dragon) within 5 time steps.

$\forall w \in warriors: w \in cave \implies \lozenge_5 w \in attack$

### At least three new villagers should be spawned during the game.

= The “spawn” ensemble should have at least two members at least 10% of the time (= 10% of 30 steps is 3).

$\lozenge^{10\%} |spawn\_farmer| \ge 2 \vee |spawn\_warrior| \ge 2$

or

$\lozenge^{3} |spawn\_farmer| \ge 2 \vee |spawn\_warrior| \ge 2$

### Warriors are mostly in the cave.

= at least half of the warriors are in the cave at least 80% of the time.

$warriors = \{ c | c \in villagers : c.role = WARRIOR \}$  
$in\_cave = \{ c | c \in villagers : c.location = CAVE \}$  
$\lozenge^{80\%} | warriors \cap in\_cave | \ge 0.5 | warriors |$

or 

$\lozenge^{80\%} | components \cap .role = WARRIOR \cap .location = CAVE | \ge 0.5 | components .role = WARRIOR |$

### When the drone’s battery is below 0.1, it should charge.

= After drone’s battery reaches 0.1 or lower, it should be in the “charging” ensemble at some point in the future.

* unless there is not enough time to reach the charger

$\forall d \in drones: d.battery \le 0.1 \wedge d.time\_to\_charger > -step \implies \lozenge d \in charging$

## DSL and parsing

* operators:
  * always(phi) for <span>\square \phi</span>
  * eventually(phi) for <span>\lozenge \phi</span>
  * eventually^n(phi) for <span>\lozenge^n \phi</span>
  * eventually_{t}(phi) for <span>\lozenge_t \phi</span>
  * Boolean logic: and, or, not, implies
  * Quantifiers: forall x in X: ...
* `lark` or `pyparsing` to build the parser
* `eval` to evaluate the constants and attribute access