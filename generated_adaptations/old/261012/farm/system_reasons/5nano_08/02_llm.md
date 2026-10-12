Reasoning and adaptation strategy

Task analysis:
- We have a set of drones (components) and a set of fields with threat levels. We must partition drones into groups: idle and one group per field to be protecting.
- The goal is to minimize bird damage by fully protecting the most threatened field whenever possible, using the closest drones.
- We should avoid over-protecting any field (no more drones than drones_for_full_protection for that field).
- We should keep drones in protection roles as stable as possible (minimize churn). At least half of the drones should be used for protection most of the time, and at least half of the drones should stay on the same field for at least 25% of time (we approximate this with a memory of previous assignments to prefer continuity).
- Partial protection is less effective; prefer fully protecting fewer fields.

Strategy description:
- Identify fields with threat_level > 0 and sort by threat level descending. The top field is the primary target.
- Ensure the primary field is fully protected if possible:
  - Current protecting drones for the primary field are counted. If there are more than the required drones_for_full_protection, reassign the excess to idle.
  - If fewer than drones_for_full_protection are protecting the primary field, assign the closest available drones to it until the field reaches its capacity or we run out of drones.
  - When choosing which drones to assign to the primary field, prefer drones that were protecting that same field in the previous step (to satisfy the continuity requirement) and then by proximity to the field center.
- After handling the primary field, consider secondary fields (ordered by threat). For each, try to fill up to its drones_for_full_protection using the remaining drones, again preferring continuity and proximity.
- If there are still drones left beyond what can protect fields fully, assign them to idle (or leave them idle if you must).
- Maintain a lightweight memory of previous assignments to prefer keeping drones on the same field across steps. We use a dict keyed by drone object id to store the last assigned group. This helps satisfy the “stay on the same field at least 25% of the time” guideline.
- Implementation uses environment.assign_group(component, group_id) for each drone, with group names:
  - "idle" for idle drones
  - "protecting {field.id}" for drones protecting a field

Notes on stability:
- The approach minimizes changes by keeping drones on a field when it is still needed and still primary. It only reassigns drones when needed to meet protection requirements.
- Drones are allocated based on distance to the field center and previous assignments to satisfy the proximity and continuity constraints.

Python implementation (class SmartFarmAdaptation)

```py
import abc
from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Memory of previous assignments: map drone_id -> group_id
        self._prev_assignments = {}

    def assign_drones(self, components, environment, group_ids, step: int):
        """
        Assign drones to groups to protect fields.
        - Always fully protect the most threatened field (to the extent possible).
        - Do not overprotect: do not assign more drones than drones_for_full_protection for a field.
        - Use as many drones as possible for protection (at least half, when feasible).
        - Maintain continuity: prefer drones that were protecting the same field in the previous step.
        """
        # Helper: distance from drone to field center
        def field_center(field):
            cx = (field.left + field.right) / 2.0
            cy = (field.top + field.bottom) / 2.0
            return cx, cy

        def dist(drone, field_center_coords):
            dx = getattr(drone.location, "x", 0.0) - field_center_coords[0]
            dy = getattr(drone.location, "y", 0.0) - field_center_coords[1]
            return (dx * dx + dy * dy) ** 0.5

        # Identify fields with threat > 0
        threat_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # If no threats, idle all drones
        if not threat_fields:
            for c in components:
                environment.assign_group(c, "idle")
                self._prev_assignments[id(c)] = "idle"
            return

        # Sort fields by threat level descending (primary target first)
        threat_fields.sort(key=lambda f: getattr(f, "threat_level", 0), reverse=True)

        # Prepare group mapping
        field_to_group = {f.id: f"protecting {f.id}" for f in threat_fields}
        # Ensure we have an "idle" group
        # (Group ids are provided; we assume "idle" exists in group_ids)

        # Cast: for each field, how many drones are currently protecting it
        current_protecting_by_field = {f.id: [] for f in threat_fields}
        for c in components:
            if getattr(c, "state", None) == "protecting":
                t = getattr(c, "target_id", None)
                if t in current_protecting_by_field:
                    current_protecting_by_field[t].append(c)

        # First, handle primary field (most threatened)
        primary = threat_fields[0]
        primary_id = primary.id
        primary_capacity = getattr(primary, "drones_for_full_protection", 0)
        current_primary = current_protecting_by_field.get(primary_id, [])
        # If over-protected, move extras to idle
        if len(current_primary) > primary_capacity:
            # Reassign farthest (by distance) to idle to reduce to capacity
            center = field_center(primary)
            # Determine distances for current primary protectors
            cur_with_dist = [(d, dist(d, center)) for d in current_primary]
            cur_with_dist.sort(key=lambda t: t[1], reverse=True)  # farthest first
            to_idle = cur_with_dist[primary_capacity:]
            for d, _ in to_idle:
                environment.assign_group(d, "idle")
                self._prev_assignments[id(d)] = "idle"
            current_primary = current_primary[:primary_capacity]

        # If under-protected, bring in closest available drones (prefer previous field if possible)
        need_primary = max(0, primary_capacity - len(current_primary))
        # Build candidate pool: drones not already protecting primary
        candidates = []
        for c in components:
            if c in current_primary:
                continue
            if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == primary_id:
                # Shouldn't happen due to previous check, but skip defensively
                continue
            candidates.append(c)

        # Sort candidates by (continuity preference, distance)
        center_primary = field_center(primary)

        def continuity_key(dr):
            prev = self._prev_assignments.get(id(dr))
            # Prefer drones that were protecting this same field previously
            if prev == f"protecting {primary_id}":
                return (0, 0.0)
            else:
                return (1, dist(dr, center_primary))

        candidates.sort(key=continuity_key)

        # Assign needed drones to primary
        assigned_to_primary = []
        for d in candidates:
            if need_primary <= 0:
                break
            group_name = f"protecting {primary_id}"
            environment.assign_group(d, group_name)
            self._prev_assignments[id(d)] = group_name
            assigned_to_primary.append(d)
            need_primary -= 1

        # Update the list of drones protecting primary after assignment
        # (we'll consider both previously protecting and newly assigned)
        final_primary = list(current_primary)
        for d in assigned_to_primary:
            final_primary.append(d)

        # After primary handling, consider other threatened fields greedily
        remaining_drones = [c for c in components if id(c) not in {id(x) for x in final_primary}]
        # We'll attempt to fill other fields in threat order, up to their capacity
        for f in threat_fields[1:]:
            fid = f.id
            capacity = getattr(f, "drones_for_full_protection", 0)
            current = current_protecting_by_field.get(fid, [])
            # If we already have more than capacity, reduce
            if len(current) > capacity:
                # Move extras to idle
                center = field_center(f)
                cur_with_dist = [(d, dist(d, center)) for d in current]
                cur_with_dist.sort(key=lambda t: t[1], reverse=True)
                to_idle = cur_with_dist[capacity:]
                for d, _ in to_idle:
                    environment.assign_group(d, "idle")
                    self._prev_assignments[id(d)] = "idle"
                current = current[:capacity]

            need = max(0, capacity - len(current))
            if need <= 0:
                continue

            # Candidate pool: drones not currently protecting this field
            candidates = [d for d in remaining_drones]
            # If some candidates are already protecting this field (shouldn't be), skip
            candidates = [d for d in candidates if getattr(d, "state", None) != "protecting" or getattr(d, "target_id", None) != fid]

            # Sort candidates by continuity (prefer those previously protecting this field) and distance
            center = field_center(f)

            def key_for_field(dr):
                prev = self._prev_assignments.get(id(dr))
                if prev == f"protecting {fid}":
                    return (0, dist(dr, center))
                return (1, dist(dr, center))

            candidates.sort(key=key_for_field)

            for d in candidates:
                if need <= 0:
                    break
                environment.assign_group(d, f"protecting {fid}")
                self._prev_assignments[id(d)] = f"protecting {fid}"
                if d in remaining_drones:
                    remaining_drones.remove(d)
                need -= 1

        # Finally, assign any drones not yet assigned to an explicit protection group to idle
        # Also ensure that every drone has a group
        all_grouped = set()
        for c in components:
            gid = getattr(c, "state", None)
            # If we already set a group, we can rely on previous assignments dict
            if id(c) in self._prev_assignments:
                environment.assign_group(c, self._prev_assignments[id(c)])
            else:
                environment.assign_group(c, "idle")
                self._prev_assignments[id(c)] = "idle"

        # Update memory for next step
        for c in components:
            # If we already assigned above, it's stored; otherwise, ensure we have an entry
            if id(c) not in self._prev_assignments:
                self._prev_assignments[id(c)] = "idle"
```