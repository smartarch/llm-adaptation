import math
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    """
    Adaptation strategy that:
    - Always fully protects the most-threatened field using the closest drones (can reassign drones protecting other fields).
    - Keeps drones already protecting the top field in place.
    - Greedily fully protects other fields only when enough remaining drones exist to reach full protection.
    - If fewer than half of drones are protecting after that, assign extra drones (closest-first) to reach at least half.
    - Explicitly assigns every drone to either "protecting {field.id}" or "idle".
    """

    def assign_drones(self, components, environment, group_ids, step: int):
        def distance_to_field_center(drone, field):
            center_x = (field.left + field.right) / 2.0
            center_y = (field.top + field.bottom) / 2.0
            dx = drone.location.x - center_x
            dy = drone.location.y - center_y
            return math.hypot(dx, dy)

        total_drones = len(components)
        if total_drones == 0:
            return

        desired_protect_count = math.ceil(total_drones / 2)

        # Threatened fields
        threatened_fields = [f for f in environment.fields if f.threat_level > 0]
        if not threatened_fields:
            # Nothing to protect => idle all
            idle_group = "idle" if "idle" in group_ids else (group_ids[0] if group_ids else "idle")
            for c in components:
                environment.assign_group(c, idle_group)
            return

        # Sort threatened fields by threat desc, tie-break by id for determinism
        threatened_fields_sorted = sorted(threatened_fields, key=lambda f: (-f.threat_level, str(f.id)))

        # Top field
        top_field = threatened_fields_sorted[0]
        top_group = f"protecting {top_field.id}"
        if top_group not in group_ids:
            # fallback: idle all if expected group missing
            idle_group = "idle" if "idle" in group_ids else (group_ids[0] if group_ids else "idle")
            for c in components:
                environment.assign_group(c, idle_group)
            return

        # Prepare containers
        field_assignments = {f.id: [] for f in threatened_fields_sorted}
        assigned_protect_ids = set()

        # Helper to get unassigned drones (by id)
        def unassigned_candidates():
            return [c for c in components if id(c) not in assigned_protect_ids]

        # 1) Keep drones already protecting the top field
        current_top = [c for c in components if c.state == "protecting" and c.target_id == top_field.id]
        for c in current_top:
            field_assignments[top_field.id].append(c)
            assigned_protect_ids.add(id(c))

        # 2) Ensure top field is fully protected by selecting closest drones from all remaining drones
        required_top = int(getattr(top_field, "drones_for_full_protection", 0))
        need_top = max(0, required_top - len(field_assignments[top_field.id]))

        if need_top > 0:
            # Candidates include all drones not currently assigned to top (this can include drones protecting other fields)
            candidates = unassigned_candidates()

            def top_key(c):
                # prefer those already moving to top field, then by distance
                moving = 0 if (c.state == "moving_to_field" and c.target_id == top_field.id) else 1
                return (moving, distance_to_field_center(c, top_field), str(c.state), id(c))

            candidates_sorted = sorted(candidates, key=top_key)
            selected = candidates_sorted[:need_top]
            for c in selected:
                field_assignments[top_field.id].append(c)
                assigned_protect_ids.add(id(c))

        # 3) Greedily fully protect other fields, but only if enough remaining drones to reach full protection.
        #    Preserve drones that are already protecting those fields among remaining candidates.
        for f in threatened_fields_sorted[1:]:
            group_name = f"protecting {f.id}"
            if group_name not in group_ids:
                continue
            # existing assigned among remaining (drones still unassigned that happen to be protecting this field)
            remaining = unassigned_candidates()
            existing_on_field = [c for c in remaining if c.state == "protecting" and c.target_id == f.id]
            # Use existing ones as starting point
            current_assigned = list(existing_on_field)
            # Compute how many needed
            required = int(getattr(f, "drones_for_full_protection", 0))
            need = max(0, required - len(current_assigned))
            # If we don't have enough remaining drones to fulfill need (including the existing_on_field already counted),
            # skip this field (to avoid partial protection). Count available candidates (excluding those already assigned elsewhere)
            available_candidates = [c for c in remaining if id(c) not in set(id(x) for x in current_assigned)]
            if len(available_candidates) < need:
                # Skip to keep preference for fully protecting fewer fields
                continue
            # Otherwise select closest among available_candidates
            def field_key(c):
                moving = 0 if (c.state == "moving_to_field" and c.target_id == f.id) else 1
                return (moving, distance_to_field_center(c, f), str(c.state), id(c))
            selected = sorted(available_candidates, key=field_key)[:need]
            # Assign existing + selected
            for c in current_assigned:
                field_assignments[f.id].append(c)
                assigned_protect_ids.add(id(c))
            for c in selected:
                field_assignments[f.id].append(c)
                assigned_protect_ids.add(id(c))

        # 4) If fewer than desired_protect_count, assign additional drones (possibly partially) to highest-threat fields
        protected_count = len(assigned_protect_ids)
        if protected_count < desired_protect_count:
            remaining_needed = desired_protect_count - protected_count
            # Iterate fields in threat order and assign closest remaining drones until we reach remaining_needed
            for f in threatened_fields_sorted:
                if remaining_needed <= 0:
                    break
                group_name = f"protecting {f.id}"
                if group_name not in group_ids:
                    continue
                candidates = unassigned_candidates()
                if not candidates:
                    break
                def key(c):
                    moving = 0 if (c.state == "moving_to_field" and c.target_id == f.id) else 1
                    return (moving, distance_to_field_center(c, f), str(c.state), id(c))
                to_take = sorted(candidates, key=key)[:remaining_needed]
                for c in to_take:
                    field_assignments[f.id].append(c)
                    assigned_protect_ids.add(id(c))
                    remaining_needed -= 1
                    if remaining_needed <= 0:
                        break

        # 5) Final explicit assignment of all drones
        idle_group = "idle" if "idle" in group_ids else (group_ids[0] if group_ids else "idle")
        # Build mapping from drone id to assigned field id for quick lookup
        drone_to_field = {}
        for fid, drones in field_assignments.items():
            for d in drones:
                drone_to_field[id(d)] = fid

        for c in components:
            cid = id(c)
            if cid in drone_to_field:
                group = f"protecting {drone_to_field[cid]}"
                if group in group_ids:
                    environment.assign_group(c, group)
                else:
                    environment.assign_group(c, idle_group)
            else:
                environment.assign_group(c, idle_group)