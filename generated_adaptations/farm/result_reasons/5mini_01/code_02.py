from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        """
        Strategy:
        - Fully protect the single most threatened field (highest threat_level > 0) using the closest drones.
        - Preserve drones that are already protecting or moving to the same field where possible.
        - Do not overprotect a field beyond its drones_for_full_protection.
        - Try to fully protect additional fields only if enough drones remain.
        - Ensure at least half of drones are used for protection; if not, allocate extra drones to next-best field(s).
        - All drones are explicitly assigned to a group ("idle" or "protecting {field.id}").
        """
        # Helper: compute center of field
        def field_center(field):
            cx = (field.left + field.right) / 2.0
            cy = (field.top + field.bottom) / 2.0
            return cx, cy

        # Helper: euclidean distance between drone and a point
        def dist_to_point(drone_loc, px, py):
            dx = drone_loc.x - px
            dy = drone_loc.y - py
            return math.hypot(dx, dy)

        # Build list of threatened fields (threat_level > 0)
        threatened_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not threatened_fields:
            # No threats: assign all drones to idle explicitly
            for comp in components:
                environment.assign_group(comp, "idle")
            return

        # Sort fields by descending threat_level
        threatened_fields.sort(key=lambda f: f.threat_level, reverse=True)

        total_drones = len(components)
        half_needed = (total_drones + 1) // 2  # at least half (ceil)

        # Prepare assignment map: component -> group_name (default idle)
        assignment = {comp: "idle" for comp in components}
        assigned_set = set()  # set of components already assigned to protecting groups

        # Helper to select best candidate drones for a particular field up to 'needed'
        def select_drones_for_field(field, needed, exclude_set):
            cx, cy = field_center(field)
            candidates = []
            for comp in components:
                if comp in exclude_set:
                    continue
                # preferences
                is_protecting = (comp.state == "protecting" and comp.target_id == field.id)
                is_moving = (comp.state == "moving_to_field" and comp.target_id == field.id)
                d = dist_to_point(comp.location, cx, cy)
                # Sorting key: prefer already protecting (True first), then moving_to_field, then closer distance
                # We use negative ints so True (1) becomes -1 and sorts ahead of 0.
                candidates.append(( -int(is_protecting), -int(is_moving), d, comp ))
            # Sort ascending so best candidates are first (since -is_protecting makes protecting ones smaller)
            candidates.sort(key=lambda t: (t[0], t[1], t[2]))
            selected = []
            for entry in candidates:
                if len(selected) >= needed:
                    break
                selected.append(entry[3])
            return selected

        # Primary field: always fully protect the most threatened field
        primary = threatened_fields[0]
        primary_group = f"protecting {primary.id}"
        primary_required = int(getattr(primary, "drones_for_full_protection", 0))
        if primary_required < 0:
            primary_required = 0

        # Select drones for primary field (prefer keep existing protectors/movers)
        selected_primary = select_drones_for_field(primary, primary_required, exclude_set=set())
        # Assign them
        for comp in selected_primary:
            assignment[comp] = primary_group
            assigned_set.add(comp)

        # Now try to fully protect other fields in descending threat order if enough drones remain
        remaining_drones = total_drones - len(assigned_set)
        for field in threatened_fields[1:]:
            if remaining_drones <= 0:
                break
            required = int(getattr(field, "drones_for_full_protection", 0))
            if required <= 0:
                continue
            # If we have enough drones to fully protect this field, do so (prefer full protection over partial)
            if remaining_drones >= required:
                selected = select_drones_for_field(field, required, exclude_set=assigned_set)
                for comp in selected:
                    assignment[comp] = f"protecting {field.id}"
                    assigned_set.add(comp)
                remaining_drones = total_drones - len(assigned_set)
            else:
                # Not enough to fully protect; skip for now to favor fewer fully-protected fields
                continue

        # Ensure at least half of drones are protecting something. If not, allocate additional drones
        current_protecting_count = sum(1 for comp, grp in assignment.items() if grp != "idle")
        if current_protecting_count < half_needed:
            # We'll allocate remaining drones to the highest-threat field(s) that are not overprotected yet
            # Iterate fields in descending threat order and fill them up with remaining drones (may result in partial protection)
            for field in threatened_fields:
                if current_protecting_count >= half_needed:
                    break
                group_name = f"protecting {field.id}"
                already = sum(1 for comp, grp in assignment.items() if grp == group_name)
                capacity = int(getattr(field, "drones_for_full_protection", 0)) - already
                if capacity <= 0:
                    continue
                need = min(capacity, half_needed - current_protecting_count)
                if need <= 0:
                    continue
                selected = select_drones_for_field(field, need, exclude_set=assigned_set)
                for comp in selected:
                    assignment[comp] = group_name
                    assigned_set.add(comp)
                    current_protecting_count += 1
                # continue until half_needed reached or no candidates

        # Final pass: assign groups using environment.assign_group
        # Make sure we never over-assign a field beyond its drones_for_full_protection:
        # If our selection accidentally assigned more (shouldn't happen), trim extra by keeping those with preference (protecting/moving/closer)
        # Enforce per-field caps
        field_to_assigned = {}
        for comp, grp in assignment.items():
            if grp == "idle":
                continue
            # Extract field id from group string
            try:
                _, fid = grp.split(" ", 1)
            except ValueError:
                fid = None
            if fid is None:
                continue
            field_to_assigned.setdefault(fid, []).append(comp)
        # Trim over-assignments
        for field in environment.fields:
            fid = str(field.id)
            if fid not in field_to_assigned:
                continue
            cap = int(getattr(field, "drones_for_full_protection", 0))
            assigned_list = field_to_assigned[fid]
            if len(assigned_list) <= cap:
                continue
            # Need to keep the best 'cap' drones according to preference
            cx, cy = field_center(field)
            scored = []
            for comp in assigned_list:
                is_protecting = (comp.state == "protecting" and comp.target_id == fid)
                is_moving = (comp.state == "moving_to_field" and comp.target_id == fid)
                d = dist_to_point(comp.location, cx, cy)
                scored.append(( -int(is_protecting), -int(is_moving), d, comp ))
            scored.sort(key=lambda t: (t[0], t[1], t[2]))
            keep = set(entry[3] for entry in scored[:cap])
            # Others become idle
            for entry in scored[cap:]:
                comp = entry[3]
                assignment[comp] = "idle"
                if comp in assigned_set:
                    assigned_set.remove(comp)

        # Now perform assignments
        for comp in components:
            grp = assignment.get(comp, "idle")
            # Validate group is allowed - if not, fallback to idle
            if grp not in group_ids:
                grp = "idle"
            environment.assign_group(comp, grp)