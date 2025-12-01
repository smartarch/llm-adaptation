from typing import List, Dict, Set, Tuple
import math
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _field_center(self, field):
        cx = (field.left + field.right) / 2.0
        cy = (field.top + field.bottom) / 2.0
        return cx, cy

    def _dist2(self, x1, y1, x2, y2):
        dx = x1 - x2
        dy = y1 - y2
        return dx * dx + dy * dy

    def assign_drones(self, components, environment, group_ids, step: int):
        # Prepare data
        drones: List = list(components)
        total_drones = len(drones)
        min_protect = math.ceil(total_drones / 2) if total_drones > 0 else 0

        # Build list of threatful fields
        fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        # Sort by threat desc, tie-breaker by id for deterministic behavior
        fields.sort(key=lambda f: (-f.threat_level, str(f.id)))

        # Helpers to build group names and check validity
        def protecting_group_name(field):
            return f"protecting {field.id}"

        IDLE_GROUP = "idle"

        # Precompute drone positions
        drone_pos = {}
        for d in drones:
            # location expected to have x and y
            loc = getattr(d, "location", None)
            if loc is None:
                drone_pos[d] = (0.0, 0.0)
            else:
                drone_pos[d] = (getattr(loc, "x", 0.0), getattr(loc, "y", 0.0))

        # Precompute field centers
        field_centers = {f.id: self._field_center(f) for f in fields}

        # Keep track of which drones are available for assignment
        available: Set = set(drones)

        # Result mapping: drone -> group_name
        assignment: Dict = {}

        # Track how many drones allocated to protecting groups
        protecting_count = 0

        # Map field_id -> list of assigned drones
        field_assignments: Dict[str, List] = {}

        # Utility to sort available drones by distance to a field
        def sort_by_distance_to_field(field):
            cx, cy = field_centers[field.id]
            # produce list of (drone, dist2)
            lst = []
            for d in available:
                x, y = drone_pos[d]
                lst.append((d, self._dist2(x, y, cx, cy)))
            lst.sort(key=lambda t: t[1])
            return [t[0] for t in lst]

        # First, ensure top-threat field is protected (even if it uses many drones)
        if fields:
            top_field = fields[0]
            top_group = protecting_group_name(top_field)
            if top_group in group_ids:
                required_top = max(0, int(getattr(top_field, "drones_for_full_protection", 0)))
                # If there are fewer total drones than required, we'll allocate all drones
                required_top = min(required_top, total_drones) if required_top > 0 else 0

                assigned = []
                # Prefer drones already protecting this field
                for d in list(available):
                    if getattr(d, "state", "") == "protecting" and getattr(d, "target_id", None) == top_field.id:
                        assigned.append(d)
                        available.remove(d)
                        if len(assigned) >= required_top:
                            break
                # Then prefer drones moving to this field
                if len(assigned) < required_top:
                    for d in list(available):
                        if getattr(d, "state", "") == "moving_to_field" and getattr(d, "target_id", None) == top_field.id:
                            assigned.append(d)
                            available.remove(d)
                            if len(assigned) >= required_top:
                                break
                # Fill with closest remaining drones
                if len(assigned) < required_top:
                    closests = sort_by_distance_to_field(top_field)
                    for d in closests:
                        if d in available:
                            assigned.append(d)
                            available.remove(d)
                            if len(assigned) >= required_top:
                                break

                # If still not enough (rare if total_drones < required_top), just take what we have
                field_assignments[top_field.id] = assigned
                protecting_count += len(assigned)

        # Second pass: try to fully protect other fields greedily by threat while we have enough available drones
        for field in fields[1:]:  # skip top which already handled
            group = protecting_group_name(field)
            if group not in group_ids:
                continue
            required = max(0, int(getattr(field, "drones_for_full_protection", 0)))
            if required <= 0:
                continue
            if len(available) >= required:
                assigned = []
                # Keep those already protecting this field if present
                for d in list(available):
                    if getattr(d, "state", "") == "protecting" and getattr(d, "target_id", None) == field.id:
                        assigned.append(d)
                        available.remove(d)
                        if len(assigned) >= required:
                            break
                # Prefer those moving to this field
                if len(assigned) < required:
                    for d in list(available):
                        if getattr(d, "state", "") == "moving_to_field" and getattr(d, "target_id", None) == field.id:
                            assigned.append(d)
                            available.remove(d)
                            if len(assigned) >= required:
                                break
                # Fill with closest
                if len(assigned) < required:
                    closests = sort_by_distance_to_field(field)
                    for d in closests:
                        if d in available:
                            assigned.append(d)
                            available.remove(d)
                            if len(assigned) >= required:
                                break
                field_assignments[field.id] = assigned
                protecting_count += len(assigned)
            else:
                # Not enough drones remaining to fully protect this field; skip for now
                continue

        # Third pass: if not enough drones are protecting (less than min_protect),
        # allocate nearest remaining drones (partially if needed) to next best fields (by threat) until threshold reached.
        if protecting_count < min_protect and available:
            # Build list of candidate fields (those with threat>0), in same order
            for field in fields:
                if protecting_count >= min_protect:
                    break
                group = protecting_group_name(field)
                if group not in group_ids:
                    continue
                # Determine how many already allocated to this field
                already = len(field_assignments.get(field.id, []))
                # Decide how many we can add here: arbitrary, but do not exceed drones_for_full_protection
                max_for_field = max(0, int(getattr(field, "drones_for_full_protection", 0)))
                can_add = max_for_field - already
                # If fully protected already, skip
                if can_add <= 0:
                    continue
                needed_to_reach = min_protect - protecting_count
                to_assign = min(can_add, needed_to_reach)
                # Assign closest available drones (prefer those moving to target)
                assigned = field_assignments.get(field.id, [])
                # Prefer moving-to-field drones
                for d in list(available):
                    if to_assign <= 0:
                        break
                    if getattr(d, "state", "") == "moving_to_field" and getattr(d, "target_id", None) == field.id:
                        assigned.append(d)
                        available.remove(d)
                        protecting_count += 1
                        to_assign -= 1
                # Fill by closest
                if to_assign > 0:
                    closests = sort_by_distance_to_field(field)
                    for d in closests:
                        if to_assign <= 0:
                            break
                        if d in available:
                            assigned.append(d)
                            available.remove(d)
                            protecting_count += 1
                            to_assign -= 1
                if assigned:
                    field_assignments[field.id] = assigned

        # Final: assign groups for drones based on field_assignments; leftover drones -> idle
        # Create reverse mapping drone -> group
        drone_to_group: Dict = {}
        for fid, drs in field_assignments.items():
            gname = protecting_group_name(next((f for f in fields if f.id == fid), None))
            # If somehow group not in group_ids, fallback to idle
            if gname not in group_ids:
                gname = IDLE_GROUP if IDLE_GROUP in group_ids else (group_ids[0] if group_ids else IDLE_GROUP)
            for d in drs:
                drone_to_group[d] = gname

        # Remaining drones go idle (or keep previous idle if IDLE group missing fallback)
        idle_group = IDLE_GROUP if IDLE_GROUP in group_ids else (group_ids[0] if group_ids else IDLE_GROUP)
        for d in drones:
            if d in drone_to_group:
                assignment[d] = drone_to_group[d]
            else:
                assignment[d] = idle_group

        # Finally, perform assignments using environment.assign_group
        for d, g in assignment.items():
            try:
                environment.assign_group(d, g)
            except Exception:
                # Be robust: if something goes wrong with assignment, attempt to assign to idle as fallback
                try:
                    environment.assign_group(d, idle_group)
                except Exception:
                    # If assignment still fails, ignore - there is no further recourse here
                    pass