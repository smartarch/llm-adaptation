from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        """
        Strategy:
        - Preserve drones currently in 'protecting' state at their target fields (if group valid).
        - Always fully protect the highest-threat field using closest drones, preferring idle drones first,
          then moving_to_field drones if needed.
        - Spread remaining drones: first give at most one drone to as many other threatened fields as possible
          (closest drone per field). Then, if drones remain, add extras to highest-threat fields (closest first)
          up to their full protection needs.
        - Any unassigned drones -> "idle".
        """
        def distance_to_field_center(drone, field):
            cx = (field.left + field.right) / 2.0
            cy = (field.top + field.bottom) / 2.0
            dx = getattr(drone.location, "x", 0) - cx
            dy = getattr(drone.location, "y", 0) - cy
            return math.hypot(dx, dy)

        def safe_assign(comp, gid):
            if gid in group_ids:
                environment.assign_group(comp, gid)
            elif "idle" in group_ids:
                environment.assign_group(comp, "idle")
            else:
                environment.assign_group(comp, group_ids[0])

        # Candidate fields (threat > 0)
        candidate_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not candidate_fields:
            for c in components:
                safe_assign(c, "idle")
            return

        # Map fields by id for quick lookup
        fields_by_id = {f.id: f for f in candidate_fields}

        # Sort candidate fields by threat desc, tie-break by id
        candidate_fields.sort(key=lambda f: (f.threat_level, f.id), reverse=True)
        top_field = candidate_fields[0]
        top_group = f"protecting {top_field.id}"
        if top_group not in group_ids:
            # cannot protect any field properly; idle all
            for c in components:
                safe_assign(c, "idle")
            return

        # Prepare metadata
        field_required = {f.id: int(getattr(f, "drones_for_full_protection", 0)) for f in candidate_fields}
        # Track assignment mapping
        assigned = {}   # comp -> group_name
        assigned_set = set()

        # 1) Preserve drones currently in 'protecting' state at their target (if valid)
        for c in components:
            if getattr(c, "state", None) == "protecting" and c.target_id is not None:
                tid = c.target_id
                group_name = f"protecting {tid}"
                if tid in fields_by_id and group_name in group_ids:
                    assigned[c] = group_name
                    assigned_set.add(c)

        # 2) Ensure top field is fully protected: count preserved assigned there, then allocate drones
        top_required = field_required.get(top_field.id, 0)
        # Count how many already assigned to top
        assigned_to_top = [c for c, g in assigned.items() if g == top_group]
        need_top = max(0, top_required - len(assigned_to_top))

        # Build pools of candidate drones (not yet assigned), prefer idle then moving_to_field then others
        not_assigned = [c for c in components if c not in assigned_set]
        idle_drones = [c for c in not_assigned if getattr(c, "state", None) == "idle"]
        moving_drones = [c for c in not_assigned if getattr(c, "state", None) == "moving_to_field"]
        other_drones = [c for c in not_assigned if getattr(c, "state", None) not in ("idle", "moving_to_field")]

        # Sort each pool by distance to top field center
        idle_drones.sort(key=lambda c: distance_to_field_center(c, top_field))
        moving_drones.sort(key=lambda c: distance_to_field_center(c, top_field))
        other_drones.sort(key=lambda c: distance_to_field_center(c, top_field))

        # Fill top field from pools in order
        for pool in (idle_drones, moving_drones, other_drones):
            if need_top <= 0:
                break
            take = pool[:need_top]
            for c in take:
                assigned[c] = top_group
                assigned_set.add(c)
            need_top -= len(take)

        # 3) Spread remaining drones to other fields
        remaining_drones = [c for c in components if c not in assigned_set]
        # Fields excluding top, sorted by threat desc
        other_fields = [f for f in candidate_fields if f.id != top_field.id]

        # First pass: give at most one drone to as many other fields as possible (closest drone per field)
        for f in other_fields:
            if not remaining_drones:
                break
            group_name = f"protecting {f.id}"
            if group_name not in group_ids:
                continue
            # choose closest remaining drone to this field
            remaining_drones.sort(key=lambda c: distance_to_field_center(c, f))
            chosen = remaining_drones.pop(0)
            assigned[chosen] = group_name
            assigned_set.add(chosen)

        # Second pass: if drones still remain, add extras to highest-threat fields up to their full requirement
        remaining_drones = [c for c in components if c not in assigned_set]
        if remaining_drones:
            # Build current counts per field from assigned
            counts = {}
            for f in candidate_fields:
                counts[f.id] = len([c for c, g in assigned.items() if g == f"protecting {f.id}"])
            # Sort fields by threat desc
            fields_by_priority = sorted(candidate_fields, key=lambda f: (f.threat_level, f.id), reverse=True)
            # For each field, try to add drones up to required
            for f in fields_by_priority:
                if not remaining_drones:
                    break
                gid = f"protecting {f.id}"
                if gid not in group_ids:
                    continue
                req = field_required.get(f.id, 0)
                already = counts.get(f.id, 0)
                need = max(0, req - already)
                if need <= 0:
                    continue
                # assign up to need drones (closest)
                remaining_drones.sort(key=lambda c: distance_to_field_center(c, f))
                take = remaining_drones[:need]
                for c in take:
                    assigned[c] = gid
                    assigned_set.add(c)
                # update remaining_drones
                remaining_drones = [c for c in components if c not in assigned_set]

        # 4) Final assignment: assign recorded groups; others -> idle
        for c in components:
            if c in assigned:
                safe_assign(c, assigned[c])
            else:
                safe_assign(c, "idle")