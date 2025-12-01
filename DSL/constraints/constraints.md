# Functional Constraints Logic implementation notes

## Semantics

* `within` operator: $\lozenge^n_t \varphi$ means that $\varphi$ holds at least $n$ times within the next $t$ steps
  * for technical reasons regarding finite traces, if the last step of the simulation is reached before $t$ steps, the constraint is not enforced (except for the case $t = MAX$ as defined below)

Derived operators:

(use the special constant $MAX$ to denote the number of steps until the end of the simulation)

* `scattered` operator: $\lozenge^n \varphi$ means that $\varphi$ holds at least $n$ times in the future
  * can be expressed as $\lozenge^n_{MAX} \varphi$

* `consequent` operator: $\square_t \varphi$ means that $\varphi$ holds in each of the next $t$ steps
  * can be expressed as $\lozenge^t_t \varphi$

* `always` operator: $\square \varphi$ means that $\varphi$ holds in each remaining step
  * can be expressed as $\square_{MAX} \varphi$ or $\lozenge^{MAX}_{MAX} \varphi$

* `once` operator: $\lozenge \varphi$ means that $\varphi$ holds at least once in the future
  * can be expressed as $\lozenge^1_{MAX} \varphi$

* `next` operator: $\bigcirc \varphi$ means that $\varphi$ holds in the next step
  * can be expressed as $\lozenge^1_1 \varphi$

Other constructs:

* standard boolean logic: `and` ($\wedge$), `or` ($\vee$), `not` ($\neg$), `implies` ($\implies$)
* quantifiers: `forall x in X: ...` ($\forall x \in X: ...$)
  * for now, don't support `exists x in X: ...` ($\exists x \in X: ...$)
* CAPITALIZED are constants
* lower_case are name of ensembles and sets of components, e.g.
  * $attack$ is the attack ensemble
  * $protecting(f)$ is the protecting ensemble for field $f$
  * $fields$ is the set of all fields (i.e., components of type Field)
* attribute access: `component.attribute` (corresponds to functions in logic, i.e. $attribute(component)$), e.g.:
  * $d.battery$ is the attribute of drone $d$ (i.e., function $battery: Drone \to float$)
  * $f.drones\_for\_full\_protection$ is the attribute of field $f$

## Examples

### Each field is not overprotected

= in each step (always), number of drones assigned to protect field (size of "protecting" ensemble) is not bigger than number of drones for full protection

$\forall f \in fields: \square |protecting(f)| \le f.drones\_for\_full\_protection$

or

$\forall f \in fields: \lozenge^{MAX}_{MAX} |protecting(f)| \le f.drones\_for\_full\_protection$

### The dragon is attacked at least once

= at least once, the attack ensemble has at least one member

$\lozenge |attack| \ge 1$

or

$\lozenge^1_{MAX} |attack| \ge 1$

### The most threatened field is fully protected

= in each step (always), the ensemble corresponding to the field with the highest threat level has at least as many drones as are required for full protection of the field

$\square |protecting(max\_threatened\_field)| \ge max\_threatened\_field.drones\_for\_full\_protection$

### If the threat level is at least 0.2 for 10 consecutive time steps, the field is fully protected

= for each field, if its threat level is at least 0.2, the field should be fully protected (as many drones assigned to the corresponding ensemble) within 10 time steps, unless the threat level drops below 0.2 during that time

$\forall f \in fields: \square_{10} f.threat\_level \ge 0.2 \implies \bigcirc |protecting(f)| \ge f.drones\_for\_full\_protection$

Note: the semantics of the implication above is that the right side is enforced on the next step after the 10 steps that the left side holds on consecutively.

#### Alternative version

= for each field, if its threat level is at least 0.2 (for at least one step), the field should be fully protected within the next 10 time steps

$\forall f \in fields: f.threat\_level \ge 0.2 \implies \lozenge_{10} \left( |protecting(f)| >= f.drones\_for\_full\_protection \vee f.treat\_level < 0.2 \right)$

### The dragon should be attacked within the first 10 steps of the game

$\lozenge_{10} |attack| \ge 1$

### After a warrior gets to the cave, it should attack the dragon (at any time in the future)

= After a warrior is in the "cave" ensemble (=he moves to the cave), they should be in the "attack" ensemble (=attack the dragon) before the game ends.

$\forall w \in warriors: \square_1 w \in cave \implies \lozenge w \in attack$

Note: the use of $\square_1$ is to ensure that the constraint is not enforced on the last step of the simulation (if the warrior moves to the cave on the last step, there is no time left to attack the dragon).

### After a warrior gets to the cave, it should attack the dragon within 5 time steps

= After a warrior is in the “cave” ensemble (=he moves to the cave), they should be in the “attack” ensemble (=attack the dragon) within 5 time steps.

$\forall w \in warriors: w \in cave \implies \lozenge_5 w \in attack$

### At least three new villagers should be spawned during the game

= The “spawn” ensemble should have at least two members at least 3 times.

$\lozenge^{3} |spawn\_farmer| \ge 2 \vee |spawn\_warrior| \ge 2$

### Warriors are mostly in the cave

= at least half of the warriors are in the cave at least 80% of the time.

$warriors = \{ c | c \in villagers : c.role = WARRIOR \}$  
$in\_cave = \{ c | c \in villagers : c.location = CAVE \}$  
$\lozenge^{0.8 \cdot MAX} | warriors \cap in\_cave | \ge 0.5 | warriors |$

### When the drone’s battery is below 0.1, it should charge

= After drone’s battery reaches 0.1 or lower, it should be in the “charging” ensemble at some point in the future (unless there is not enough time to reach the charger)

$\forall d \in drones: \square_{d.time\_to\_charger} d.battery \le 0.1 \implies \lozenge d \in charging$

## Parsing and implementation notes

* we use a `lark` grammar for parsing the (simplified) FCL: [`grammar-simple.lark`](./grammar-simple.lark)
* `eval` to evaluate the constants and attribute access

Variables available in the evaluation context:

* ensembles
  * for each ensemble type `Type` with params:
    * `TypeEns` = dict of all ensemble instances of that type indexed by their parameter (component)
  * for each ensemble type `Type` without params (singleton):
    * `TypeEn` = the first ensemble instance of that type
* components
  * for each component type `Type`:
    * `TypeComps` = list of all components of that type
* defined local variables (via Python `eval`)

### Temporal operators

* evaluate -> return True / False, or list of obligations to be checked in the next steps
* Python expressions (in backticks) are used for formulas (attribute access, ensemble membership, size of ensembles, constants, logical operators, etc.)

* store history for each operator (boolean for each previous step)
  * used when temporal operator is at the left side of an implication
* obligations -> if a temporal operator should hold, store the obligation and check it in each following step
  * used when temporal operator is at the right side of an implication
  * used when temporal operator is not in an implication (top-level)
* store history / obligations for each of "bindings" (i.e., variable assignment in `forall`)
