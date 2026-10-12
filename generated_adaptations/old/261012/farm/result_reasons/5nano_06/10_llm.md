Reasoning and adaptation strategy

Goal:
- Minimize field damage by allocating drones to field-protecting groups.
- The strongest protection effect comes from fully protecting as many of the most-threatened fields as possible, given the drone budget.
- Avoid partial protections; focus on fully protecting top fields first, then ensure a healthy level of protection (at least half of drones) without overprotecting any field.
- Reduce drone churn by biasing allocations toward drones that were already protecting the same field (stability) and by using proximity (distance to field center) to choose the closest drones when reallocation is needed.
- Re-assign every step explicitly to a group.

Improvements in this version:
- Global greedy allocation in threat order: fully protect top fields in threat order, each up to drones_for_full_protection.
- Stronger stability bias: prefer drones already protecting a given field when reallocating to that field; otherwise bias toward idle drones before moving drones from other fields.
- Distance-aware selection with explicit stability tie-breakers to minimize travel time and churn.
- After maximizing fully protected fields, ensure at least half of drones are protecting by filling additional fields, but never exceeding their per-field capacity.
- Clear, deterministic fallback to idle if a target group is not available.

High-level approach:
1) Gather threatened fields, sort by threat_level descending.
2) For each field in that order, allocate drones to its protecting group up to drones_for_full_protection, using:
   - Drones already in that field’s protecting group first (to minimize churn).
   - Then closest available drones, with a bias to drones that were already protecting that field.
3) If any field ends up over-protected, demote the farthest drones to idle.
4) After fulfilling as many fully protected fields as possible, check if at least half of the drones are protecting. If not, allocate additional drones to the next-threatened fields up to their capacity, using the same proximity/stability bias.
5) Finally, assign any remaining drones to idle. Update per-drone memory to bias future steps.

Python code:

```py
import math

# Assuming the base class can be imported as described
from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Memory of last group assignment for each drone (by id)
        self.prev_group = {}

    def _center_of_field(self, f):
        return ((f.left + f.right) / 2.0, (f.top + f.bottom) / 2.0)

    def _dist_to_point(self, drone, cx, cy):
        loc = getattr(drone, "location", None)
        if loc is None:
            return float("inf")
        dx = getattr(loc, "x", 0.0) - cx
        dy = getattr(loc, "y", 0.0) - cy
        return math.hypot(dx, dy)

    def assign_drones(self, components, environment, group_ids, step: int):
        """
        Divide drones into:
        - idle: drones doing nothing
        - protecting {field_id}: drones protecting a specific field

        Strategy:
        - Fully protect the top threatened fields first, in threat order, up to drones_for_full_protection per field.
        - Use the closest drones to fill each field, biasing towards drones that already protect that field.
        - Do not oversubscribe a field beyond drones_for_full_protection.
        - After maximizing fully protected fields, ensure at least half of drones are protecting, if possible.
        - All remaining drones are idle. Explicitly re-assign every drone this step.
        """
        # Gather fields with positive threat
        fields_with_threat = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # If no threat, idle all drones
        if not fields_with_threat:
            for c in components:
                environment.assign_group(c, "idle")
                self.prev_group[id(c)] = "idle"
            return

        # Sort fields by threat level descending
        fields_with_threat.sort(key=lambda f: f.threat_level, reverse=True)

        total_drones = len(components)
        half_target = (total_drones + 1) // 2

        # Step 1: fully protect each threatened field in threat order
        def group_for(field):
            return f"protecting {field.id}"

        for field in fields_with_threat:
            grp = group_for(field)
            if grp not in group_ids:
                continue  # skip if no valid group for this field

            required = int(getattr(field, "drones_for_full_protection", 0))

            # Current drones assigned to this group
            current = [d for d in components if self.prev_group.get(id(d)) == grp]
            current_count = len(current)

            need = max(0, required - current_count)
            if need <= 0:
                # If there are more drones than required, demote extras to idle
                if current_count > required:
                    cx, cy = self._center_of_field(field)
                    current_sorted = sorted(current, key=lambda d: self._dist_to_point(d, cx, cy), reverse=True)
                    to_idle = current_sorted[: current_count - required]
                    for d in to_idle:
                        environment.assign_group(d, "idle")
                        self.prev_group[id(d)] = "idle"
                continue

            # Pool of candidates not currently in this field
            pool = [d for d in components if self.prev_group.get(id(d)) != grp]

            center = self._center_of_field(field)

            def pool_key(d):
                bias = 0 if self.prev_group.get(id(d)) == grp else 1
                return (bias, self._dist_to_point(d, center[0], center[1]))

            pool_sorted = sorted(pool, key=pool_key)

            for d in pool_sorted[:need]:
                environment.assign_group(d, grp)
                self.prev_group[id(d)] = grp
                current.append(d)

            # After addition, prune overshoot
            if len(current) > required:
                cx, cy = center
                current_sorted = sorted(current, key=lambda d: self._dist_to_point(d, cx, cy), reverse=True)
                to_idle = current_sorted[: len(current_sorted) - required]
                for d in to_idle:
                    environment.assign_group(d, "idle")
                    self.prev_group[id(d)] = "idle"
                    current.remove(d)

        # Step 2: ensure at least half of drones are protecting, if possible
        protecting_groups = [f"protecting {f.id}" for f in fields_with_threat]
        protecting_count = sum(
            1 for d in components if self.prev_group.get(id(d), "") in protecting_groups
        )

        if protecting_count < half_target:
            for field in fields_with_threat:
                grp = group_for(field)
                if grp not in group_ids:
                    continue

                required = int(getattr(field, "drones_for_full_protection", 0))
                current = [d for d in components if self.prev_group.get(id(d)) == grp]
                current_count = len(current)
                if current_count >= required:
                    continue

                pool = [d for d in components if self.prev_group.get(id(d)) != grp]
                center = self._center_of_field(field)

                def pool_key2(d):
                    bias = 0 if self.prev_group.get(id(d)) == grp else 1
                    return (bias, self._dist_to_point(d, center[0], center[1]))

                pool_sorted = sorted(pool, key=pool_key2)
                needed = min(required - current_count, len(pool_sorted))

                for d in pool_sorted[:needed]:
                    environment.assign_group(d, grp)
                    self.prev_group[id(d)] = grp
                    current.append(d)
                    protecting_count += 1
                    if protecting_count >= half_target:
                        break
                if protecting_count >= half_target:
                    break

        # Step 3: assign any remaining drones to idle
        for d in components:
            if self.prev_group.get(id(d)) is None:
                environment.assign_group(d, "idle")
                self.prev_group[id(d)] = "idle"
```