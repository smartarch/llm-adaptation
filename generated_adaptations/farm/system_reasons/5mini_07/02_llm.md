Reasoning and strategy

Goal recap
- Always fully protect the single most threatened field (highest threat_level) using the closest drones, using exactly the number of drones required (field.drones_for_full_protection).
- Avoid overprotection: don't assign more drones than needed to any field.
- Keep assignments stable: prefer to keep drones that already have been assigned to a field; avoid moving drones that have been in the same group for a while.
- Use at least half of available drones for protection most of the time. After securing the top field fully, use remaining drones to fully protect other high-threat fields (in descending threat) until we either run out of drones or reach the goal of at least half the drones protecting fields.
- Prefer fully protecting fewer fields rather than partially protecting many.
- When choosing which drones should protect a field, pick drones minimizing a score combining distance to the field center and a small penalty for moving drones that have been assigned to a different group for a long time. This ensures the protecting drones are close while also biasing to keep longer-running assignments.

State we maintain
- For assignment stability, the strategy keeps a small internal history per drone:
  - last assigned group (string)
  - step when that assignment began
This allows us to avoid reassigning drones that have been in the same group for a while.

High-level algorithm per adaptation step
1. Build list of candidate protecting groups (only for fields with threat_level > 0).
2. Identify the most threatened field (highest threat_level). Determine how many drones are required to fully protect it.
3. Choose the best drones for that field:
   - Compute a score for each drone = distance_to_field_center + penalty_for_changing,
     where penalty_for_changing is small for drones that have stayed long in their group and zero for drones already assigned to that field. This biases towards keeping long-standing assignments but still emphasizes closeness.
   - Keep exactly the required number of drones for the field, preferring to keep long-standing protectors when there are more already protecting than needed.
4. After securing the top field, attempt to fully protect other high-threat fields (descending threat) until either:
   - we run out of drones, or
   - we've allocated at least half of all drones to protecting groups (whichever comes first).
   For each additional field we pick the required number of best remaining drones by the same scoring rule.
5. Assign all leftover drones to "idle".
6. Update the internal history for each drone (group and since-step).
7. Use environment.assign_group(component, group_id) for every drone.

Practical choices / parameter notes
- Distance is Euclidean from drone.location to the center of the field rectangle.
- Change penalty = 0 if drone's last assigned group already protects that field; else = 0.02 * since_steps. The multiplier (0.02) is small so distance predominates but long-term assignments are still respected.
- If no history exists for a drone on the first call, we seed its last group from the observed component.state and component.target_id if possible; otherwise 'idle'.
- When we must drop extra protecting drones for a field (over the requirement), we keep the ones that have been there the longest (stability).

The implementation follows the FarmAdaptation API and calls environment.assign_group for every component.

Code

```py
from typing import Dict, Any, List, Tuple
import math

from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # history: drone_key -> {"group": group_id, "since": step}
        self._history: Dict[Any, Dict[str, Any]] = {}

    def _drone_key(self, component):
        # Prefer a stable 'id' attribute if present, otherwise use Python id()
        return getattr(component, "id", id(component))

    def _field_center(self, field):
        cx = (field.left + field.right) / 2.0
        cy = (field.top + field.bottom) / 2.0
        return cx, cy

    def _distance(self, loc, fx, fy):
        dx = (getattr(loc, "x", 0.0) - fx)
        dy = (getattr(loc, "y", 0.0) - fy)
        return math.hypot(dx, dy)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Prepare drone keys and ensure history entries exist (seed from observed state)
        drone_infos = {}
        for comp in components:
            key = self._drone_key(comp)
            # Determine an initial/observed group name if we don't have one recorded
            if key not in self._history:
                # Try to infer observed group from component.state and target_id
                if getattr(comp, "state", None) == "protecting" and getattr(comp, "target_id", None) is not None:
                    inferred_group = f"protecting {comp.target_id}"
                else:
                    inferred_group = "idle"
                self._history[key] = {"group": inferred_group, "since": step}
            drone_infos[key] = {"component": comp, "last_group": self._history[key]["group"], "since": self._history[key]["since"]}

        total_drones = len(components)
        min_protectors_target = math.ceil(total_drones / 2)

        # Build list of fields with positive threat
        fields = [f for f in getattr(environment, "fields", []) if getattr(f, "threat_level", 0) > 0]
        if not fields:
            # No threatened fields: assign everyone to idle and update history
            for comp in components:
                env_group = "idle"
                environment.assign_group(comp, env_group)
                key = self._drone_key(comp)
                if self._history.get(key, {}).get("group") != env_group:
                    self._history[key] = {"group": env_group, "since": step}
            return

        # Sort fields by threat descending (most threatened first)
        fields_sorted = sorted(fields, key=lambda f: getattr(f, "threat_level", 0), reverse=True)

        # Helper: compute candidates and scores for a given field
        def score_for_field(field):
            fx, fy = self._field_center(field)
            scores = []
            for key, info in drone_infos.items():
                comp = info["component"]
                dist = self._distance(comp.location, fx, fy)
                last_group = info["last_group"]
                since = info["since"]
                since_steps = max(0, step - since)
                # Penalty for reassigning a drone that has been stable for a while.
                # If drone already assigned to protect this field, penalty = 0 to prefer keeping it.
                desired_group = f"protecting {field.id}"
                if last_group == desired_group:
                    penalty = 0.0
                else:
                    # small penalty proportional to how long drone has been in its current group
                    penalty = 0.02 * float(since_steps)
                scores.append((key, dist + penalty, dist, penalty, since_steps))
            # sort by composite score, smaller is better
            scores.sort(key=lambda x: (x[1], x[2], -x[4]))
            return scores

        # Allocation result: group_name -> list of drone keys
        allocation: Dict[str, List[Any]] = {}
        assigned_keys = set()

        # Function to allocate k best drones for a field (by key)
        def allocate_for_field(field, k):
            desired_group = f"protecting {field.id}"
            if desired_group not in group_ids:
                return []  # group not valid (shouldn't happen), skip
            candidates = score_for_field(field)
            chosen = []
            # First consider drones already assigned to this group and not yet counted
            already = [c for c in candidates if drone_infos[c[0]]["last_group"] == desired_group and c[0] not in assigned_keys]
            # Keep the longest-serving ones first when trimming
            already_sorted = sorted(already, key=lambda x: (x[3], -x[4]))  # minimal penalty first, prefer larger since_steps
            for tup in already_sorted:
                if len(chosen) >= k:
                    break
                key = tup[0]
                chosen.append(key)
                assigned_keys.add(key)
            # If not enough, pick from remaining candidates excluding already assigned keys
            if len(chosen) < k:
                for key, _, _, _, _ in candidates:
                    if key in assigned_keys:
                        continue
                    chosen.append(key)
                    assigned_keys.add(key)
                    if len(chosen) >= k:
                        break
            # finalize allocation
            allocation[desired_group] = allocation.get(desired_group, []) + chosen
            return chosen

        # 1) Fully protect the most threatened field
        top_field = fields_sorted[0]
        need_top = max(0, int(getattr(top_field, "drones_for_full_protection", 0)))
        # Ensure at least need_top is allocated (if there are fewer drones than need_top, allocate as many as possible)
        need_top = min(need_top, total_drones)
        allocated_for_top = allocate_for_field(top_field, need_top)

        # 2) Try to fully protect additional fields (in descending threat) until we've used at least half the drones or ran out
        protected_count = sum(len(v) for v in allocation.values())
        # Consider subsequent fields
        for field in fields_sorted[1:]:
            if protected_count >= min_protectors_target:
                break
            need = max(0, int(getattr(field, "drones_for_full_protection", 0)))
            # If we don't have enough remaining drones to fully protect, skip (prefer full protection)
            remaining = total_drones - len(assigned_keys)
            if need <= 0 or need > remaining:
                continue
            chosen = allocate_for_field(field, need)
            if not chosen:
                continue
            protected_count = sum(len(v) for v in allocation.values())

        # 3) Ensure we didn't over-allocate to any field beyond its drones_for_full_protection
        # (Allocation function should respect this, but if more happened due to ties, trim)
        for field in fields_sorted:
            g = f"protecting {field.id}"
            if g not in allocation:
                continue
            max_needed = max(0, int(getattr(field, "drones_for_full_protection", 0)))
            if len(allocation[g]) > max_needed:
                # Decide which to keep: prefer those with longer since times
                kept = allocation[g]
                kept_sorted = sorted(kept, key=lambda k: (drone_infos[k]["since"],))  # earlier since means longer-serving
                allocation[g] = kept_sorted[:max_needed]
                # free others
                for freed in kept_sorted[max_needed:]:
                    assigned_keys.discard(freed)

        # 4) Any drone not in assignment -> idle
        final_assignments: Dict[Any, str] = {}
        for key, info in drone_infos.items():
            assigned = None
            for g, keys in allocation.items():
                if key in keys:
                    assigned = g
                    break
            if assigned is None:
                assigned = "idle"
            final_assignments[key] = assigned

        # 5) Commit assignments via environment.assign_group and update history
        for key, info in drone_infos.items():
            comp = info["component"]
            group = final_assignments[key]
            # Ensure the group name is valid; otherwise fall back to idle
            if group not in group_ids:
                group = "idle"
            environment.assign_group(comp, group)
            prev = self._history.get(key)
            if prev is None or prev.get("group") != group:
                # update start step for new assignment
                self._history[key] = {"group": group, "since": step}
            # else keep previous since

        # End of assign_drones
```