import math
from typing import List
from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components: List, environment, group_ids: List[str], step: int):
        """
        Assign drones to groups:
        - "idle" for idle drones
        - "protecting {field_id}" for protected fields (one group per field with threat > 0)

        Strategy:
        - Fully protect the most threatened field if possible, using the closest drones.
        - Use remaining drones to protect other threatened fields up to their full_protection requirements.
        - Maintain persistence: do not move drones unnecessarily; prioritize drones already heading to or protecting a field.
        - Keep at least 50% of drones protecting when possible.
        """

        # Helpers
        def field_center(f):
            cx = (f.left + f.right) / 2.0
            cy = (f.top + f.bottom) / 2.0
            return (cx, cy)

        def distance(drone, f):
            # drone.location is expected to have x, y
            loc = drone.location
            if loc is None:
                return float('inf')
            fx, fy = field_center(f)
            dx = loc.x - fx
            dy = loc.y - fy
            return math.hypot(dx, dy)

        # Build field map and list of threatened fields
        fields = list(environment.fields)
        field_map = {f.id: f for f in fields}
        threatened_fields = [f for f in fields if getattr(f, "threat_level", 0) > 0]

        # If no field is threatened, all drones go idle
        if not threatened_fields:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Sort threatened fields by threat level descending
        threatened_fields.sort(key=lambda ff: ff.threat_level, reverse=True)

        # Group IDs available
        # Ensure we know the exact group name for each field
        field_group_name = {f.id: f"protecting {f.id}" for f in threatened_fields}
        # (Note: group_ids is provided, but the exact strings we generate must match these names.)

        total_drones = len(components)
        half_threshold = math.ceil(total_drones * 0.5)

        # Initialize target_group for each drone based on current state to preserve persistence.
        # If a drone is currently protecting a field or heading to one, map it to that protecting group.
        # Otherwise map to idle.
        target_group = {}
        for d in components:
            # If drone has a target, assume it's heading to that field
            if getattr(d, "target_id", None) is not None:
                tid = d.target_id
                group = f"protecting {tid}"
            else:
                # If no target, consider it idle by default
                group = "idle"
            target_group[d] = group

        # Helper: count currently protecting the top field
        top_field = threatened_fields[0]
        current_top_protect = sum(1 for d in components
                                  if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == top_field.id)

        # Step 1: Fully protect the top field if possible
        needed_top = max(0, getattr(top_field, "drones_for_full_protection", 0) - current_top_protect)
        assigned_top = 0

        if needed_top > 0:
            # Candidate drones not currently protecting the top field (prefer closer)
            candidates = []
            for d in components:
                current_group = target_group.get(d, "idle")
                if current_group != f"protecting {top_field.id}":
                    dist_to_top = distance(d, top_field)
                    candidates.append((dist_to_top, d))
            candidates.sort(key=lambda t: t[0])

            # Assign as many as needed from closest candidates
            for _, d in candidates:
                if assigned_top >= needed_top:
                    break
                # Only reassign if it's beneficial (i.e., not already protecting the top field)
                target_group[d] = f"protecting {top_field.id}"
                assigned_top += 1

            # If still not enough, as a last resort take from drones protecting other fields
            if assigned_top < needed_top:
                remaining = needed_top - assigned_top
                other_protecting = [(distance(d, top_field), d) for d in components
                                    if target_group.get(d, "idle") != f"protecting {top_field.id}"
                                    and getattr(d, "state", None) == "protecting"
                                    and getattr(d, "target_id", None) != top_field.id]
                other_protecting.sort(key=lambda t: t[0])
                for _, d in other_protecting:
                    if remaining <= 0:
                        break
                    target_group[d] = f"protecting {top_field.id}"
                    assigned_top += 1
                    remaining -= 1

        # Step 2: Allocate to other threatened fields to meet full protection as possible
        # After top field is addressed, attempt to fill other fields to their full_protection where possible
        # We'll iteratively allocate from closest drones (not currently protecting that target)
        assigned_any = True
        # Loop over threatened fields in threat order (excluding the top field which we already handled)
        for f in threatened_fields[1:]:
            field_id = f.id
            group_name = f"protecting {field_id}"
            current_count = sum(1 for d in components
                                if target_group.get(d, "") == group_name)
            needed = max(0, getattr(f, "drones_for_full_protection", 0) - current_count)
            if needed <= 0:
                continue

            # Candidates: drones not currently protecting this field (prefer not to break existing protection)
            candidates = []
            for d in components:
                if target_group.get(d, "") != group_name:
                    dist_to_f = distance(d, f)
                    candidates.append((dist_to_f, d))
            candidates.sort(key=lambda t: t[0])

            # Allocate needed drones from closest candidates
            allocated = 0
            for _, d in candidates:
                if allocated >= needed:
                    break
                target_group[d] = group_name
                allocated += 1

        # After attempting to fill full protections, ensure at least half of drones are protecting when possible.
        # Compute current total protecting drones from our target_group mapping
        current_total_protecting = sum(1 for d in components if target_group.get(d, "").startswith("protecting "))

        # If below threshold, attempt to add more protective assignments from idle/movable drones
        if current_total_protecting < half_threshold:
            remaining_needed = half_threshold - current_total_protecting

            # Gather all potential drones not already protecting a field, in order of closeness to their best field (top priority: top_field)
            # We'll try to allocate to the top field first (if still not full) or to the next most threatened field with available capacity
            # Build a list of fields by threat (excluding already fully protected ones)
            fields_by_threat = [f for f in threatened_fields if f.id in field_map]
            fields_by_threat.sort(key=lambda ff: ff.threat_level, reverse=True)

            # Build a set of fields that still need more drones to reach full protection
            still_needing = []
            for f in fields_by_threat:
                cid = sum(1 for d in components if target_group.get(d, "") == f"protecting {f.id}")
                need = max(0, getattr(f, "drones_for_full_protection", 0) - cid)
                if need > 0:
                    still_needing.append((f, need))

            if still_needing:
                # Create a pool of idle/movable drones to allocate from
                available = []
                for d in components:
                    if target_group.get(d, "") != f"protecting {still_needing[0][0].id}":
                        available.append((distance(d, still_needing[0][0]), d))
                available.sort(key=lambda t: t[0])

                # First try to allocate to the highest-threat field that still needs, then proceed to next
                for f, need in still_needing:
                    if remaining_needed <= 0:
                        break
                    target_group_name = f"protecting {f.id}"
                    # Recompute candidates for this field
                    candidates = []
                    for d in components:
                        if target_group.get(d, "") != target_group_name:
                            dist_to_f = distance(d, f)
                            candidates.append((dist_to_f, d))
                    candidates.sort(key=lambda t: t[0])

                    for _, d in candidates:
                        if remaining_needed <= 0:
                            break
                        # Assign drone to this field
                        target_group[d] = target_group_name
                        remaining_needed -= 1
                        current_total_protecting += 1
                        if remaining_needed <= 0:
                            break

        # Final step: write assignments to environment
        for d in components:
            group = target_group.get(d, "idle")
            # Ensure the group name is exactly one of the allowed group_ids
            # If a mismatch occurs (e.g., a field got removed), fallback to idle or closest valid group
            if group not in group_ids:
                # Try to map to an existing protecting group for a field it is assigned to
                if getattr(d, "target_id", None) is not None:
                    candidate = f"protecting {d.target_id}"
                    if candidate in group_ids:
                        group = candidate
                    else:
                        group = "idle"
                else:
                    group = "idle"
            environment.assign_group(d, group)