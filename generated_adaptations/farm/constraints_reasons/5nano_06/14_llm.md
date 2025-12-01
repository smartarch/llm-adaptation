Strategy rationale to reduce damage

Key ideas:
- The top-field must always be fully protected whenever possible. This constraint remains sacrosanct.
- After ensuring the primary field is fully protected, allocate drones to other fields in a way that maximizes overall field protection while minimizing drone travel. This means:
  - Prioritize protecting the next-threat fields up to their full protection quota, but only using idle drones when possible to avoid unnecessary churn.
  - If there are still drones after fully protecting as many fields as possible, reinforce the primary field again (to keep it fully protected) and then consider additional fields with a proximity bias.
  - Use a multi-stage allocation with explicit reinforcement steps to strictly avoid violating the “primary field fully protected first” rule, while still increasing the number of fully protected fields over time.

What changed:
- Introduce a reinforcement pass that, if the primary field isn’t currently at drones_for_full_protection, assigns the closest drones to the primary field to reach that quota.
- After the primary is fully protected, allocate drones greedily to other fields, first to complete their own full protection quotas (using idle drones when possible), then to ensure at least half of drones are protecting something. No partial protections are relied upon as the primary protection mechanism.
- Drones are allocated based on distance to their target field to minimize travel time, improving protection timing and reducing damage.

Code:

```py
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Memory: map each drone object to the group it's assigned to
        self._memory_assigned = {}

    def assign_drones(self, components, environment, group_ids, step: int):
        # Collect fields with positive threat level
        fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not fields:
            for d in components:
                environment.assign_group(d, "idle")
                self._memory_assigned[d] = "idle"
            return

        fields_sorted = sorted(fields, key=lambda f: f.threat_level, reverse=True)
        primary_field = fields_sorted[0]
        primary_group = f"protecting {primary_field.id}"

        N = len(components)
        half = N // 2

        def field_center(field):
            cx = (field.left + field.right) / 2.0
            cy = (field.top + field.bottom) / 2.0
            return cx, cy

        def dist_to_field(drone, field):
            cx, cy = field_center(field)
            loc = getattr(drone, "location", None)
            if loc is None:
                return float("inf")
            dx = getattr(loc, "x", 0.0) - cx
            dy = getattr(loc, "y", 0.0) - cy
            return (dx * dx + dy * dy) ** 0.5

        new_assignments = {}

        # Stage A: initial primary protection (closest drones)
        n_needed = getattr(primary_field, "drones_for_full_protection", 0) or 0
        if n_needed > 0 and len(components) > 0:
            distances = [(dist_to_field(d, primary_field), d) for d in components]
            distances.sort(key=lambda t: t[0])
            take = min(n_needed, len(distances))
            for i in range(take):
                _, d = distances[i]
                new_assignments[d] = primary_group

        # Stage A2: reinforcement pass to ensure primary_field reaches n_needed
        if n_needed > 0:
            current_primary = [d for d in components if new_assignments.get(d) == primary_group]
            if len(current_primary) < n_needed:
                candidates = [(dist_to_field(d, primary_field), d) for d in components]
                candidates.sort(key=lambda t: t[0])
                for dist, d in candidates:
                    if d in current_primary:
                        continue
                    new_assignments[d] = primary_group
                    current_primary.append(d)
                    if len(current_primary) >= n_needed:
                        break

        # Stage B: after primary is fully protected, ensure at least half protected
        primary_assigned = sum(1 for d in components if new_assignments.get(d) == primary_group)
        primary_fully_protected = (primary_assigned >= n_needed) if n_needed > 0 else True

        protected_now = sum(1 for d in components if new_assignments.get(d, None) is not None and new_assignments.get(d) != "idle")

        if primary_field and primary_fully_protected:
            if protected_now < half:
                remaining_slots = half - protected_now
                for field in fields_sorted[1:]:
                    grp = f"protecting {field.id}"
                    n_limit = getattr(field, "drones_for_full_protection", 0) or 0

                    current_in_field = [d for d in components if new_assignments.get(d) == grp]
                    if len(current_in_field) >= n_limit:
                        continue

                    can_take = min(n_limit - len(current_in_field), remaining_slots)
                    if can_take <= 0:
                        continue

                    candidates = []
                    for d in components:
                        if new_assignments.get(d) == grp:
                            continue
                        dist = dist_to_field(d, field)
                        candidates.append((dist, d))
                    candidates.sort(key=lambda t: t[0])

                    for i in range(min(can_take, len(candidates))):
                        _, d = candidates[i]
                        new_assignments[d] = grp
                    remaining_slots = max(0, remaining_slots - can_take)
                    if remaining_slots == 0:
                        break

        # Stage F: reinforcement pass to fill additional fields using idle drones (closest first)
        if primary_field:
            n_needed = getattr(primary_field, "drones_for_full_protection", 0) or 0
            current_primary = [d for d in components if new_assignments.get(d) == primary_group]
            if len(current_primary) < n_needed:
                candidates = [(dist_to_field(d, primary_field), d) for d in components]
                candidates.sort(key=lambda t: t[0])
                for dist, d in candidates:
                    if new_assignments.get(d) == primary_group:
                        continue
                    new_assignments[d] = primary_group
                    current_primary.append(d)
                    if len(current_primary) >= n_needed:
                        break

        # Stage G: use idle drones to reinforce other fields (fully protect if possible)
        idle_drones = [d for d in components if new_assignments.get(d) == "idle"]
        for field in fields_sorted[1:]:
            grp = f"protecting {field.id}"
            n_limit = getattr(field, "drones_for_full_protection", 0) or 0
            current_in_field = [d for d in components if new_assignments.get(d) == grp]
            if len(current_in_field) >= n_limit:
                continue
            while idle_drones and len(current_in_field) < n_limit:
                d = idle_drones.pop(0)
                new_assignments[d] = grp
                current_in_field.append(d)

        # Stage H: remaining drones become idle
        for d in components:
            if d not in new_assignments:
                new_assignments[d] = "idle"

        # Apply
        for d, grp in new_assignments.items():
            if grp not in group_ids:
                grp = "idle"
            environment.assign_group(d, grp)
            self._memory_assigned[d] = grp
```