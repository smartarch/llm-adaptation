from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Helpers
        def field_center(field):
            return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

        def dist2(loc, px, py):
            dx = loc.x - px
            dy = loc.y - py
            return dx * dx + dy * dy

        total_drones = len(components)
        min_protect_needed = (total_drones + 1) // 2  # ceil(total/2)

        # Gather threatened fields (threat_level > 0) and sort by descending threat, then id for determinism
        threatened = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not threatened:
            # No threats: assign all drones to idle if available
            idle_group = "idle" if "idle" in group_ids else None
            if idle_group:
                for comp in components:
                    environment.assign_group(comp, idle_group)
            else:
                # fallback: no idle group provided; try to preserve current protecting groups where valid
                for comp in components:
                    if comp.target_id:
                        grp = f"protecting {comp.target_id}"
                        if grp in group_ids:
                            environment.assign_group(comp, grp)
            return

        threatened.sort(key=lambda f: (-f.threat_level, str(getattr(f, "id", ""))))

        # We'll build a list of (component, group) and a set of assigned ids to ensure each comp is assigned once
        assignments = []
        assigned_ids = set()

        # Helper to mark assignment (does not call environment.assign_group yet)
        def mark_assign(comp, group):
            cid = id(comp)
            if cid in assigned_ids:
                return False
            assigned_ids.add(cid)
            assignments.append((comp, group))
            return True

        # Function to assign protection for one field: follows rules described
        def allocate_for_field(field, require_closest=False):
            """
            require_closest: if True, select closest drones among all components (used for highest-threat behavior
            when field is not already fully protected). If field already has enough committed drones, keep those
            and do not pick additional closest ones.
            """
            group_name = f"protecting {field.id}"
            if group_name not in group_ids:
                return 0  # cannot assign to this field if group not present

            required = int(getattr(field, "drones_for_full_protection", 0))
            if required <= 0:
                return 0

            # Find currently committed drones (target_id == field.id) among all components
            committed = [c for c in components if getattr(c, "target_id", None) == field.id]
            # Count how many of those are not yet assigned
            committed_unassigned = [c for c in committed if id(c) not in assigned_ids]
            assigned_here = 0

            # If require_closest is True and there are fewer committed than required, we will pick additional closest
            if require_closest:
                if len(committed) >= required:
                    # Already fully protected by committed drones => keep those committed (but only up to required)
                    for c in committed_unassigned[:required]:
                        if mark_assign(c, group_name):
                            assigned_here += 1
                    return assigned_here
                else:
                    # Need to pick the required number of closest drones among all unassigned components.
                    cx, cy = field_center(field)
                    # Consider all components (including those committed elsewhere) that are currently unassigned
                    candidates = [c for c in components if id(c) not in assigned_ids]
                    candidates.sort(key=lambda c: dist2(c.location, cx, cy))
                    for c in candidates[:required]:
                        if mark_assign(c, group_name):
                            assigned_here += 1
                    return assigned_here
            else:
                # For non-highest fields: keep committed_unassigned first (they prefer that field),
                # then pick closest among remaining unassigned if needed.
                for c in committed_unassigned:
                    if assigned_here >= required:
                        break
                    if mark_assign(c, group_name):
                        assigned_here += 1
                if assigned_here >= required:
                    return assigned_here
                # Need additional drones: pick closest among currently unassigned components
                cx, cy = field_center(field)
                candidates = [c for c in components if id(c) not in assigned_ids]
                candidates.sort(key=lambda c: dist2(c.location, cx, cy))
                need = required - assigned_here
                for c in candidates[:need]:
                    if mark_assign(c, group_name):
                        assigned_here += 1
                return assigned_here

        # 1) Always fully protect the highest-threat field using closest drones (unless it's already fully protected by committed drones)
        highest = threatened[0]
        allocate_for_field(highest, require_closest=True)

        # Count how many assigned to protecting groups so far
        protect_count = sum(1 for _, g in assignments if g.startswith("protecting "))
        # 2) If we don't meet the half-threshold, iterate other threatened fields (by threat descending)
        idx = 1
        while protect_count < min_protect_needed and idx < len(threatened):
            f = threatened[idx]
            added = allocate_for_field(f, require_closest=False)
            if added == 0:
                # nothing could be assigned to this field (maybe group missing), move on
                idx += 1
                continue
            protect_count += added
            idx += 1

        # 3) Any remaining unassigned drones -> idle if possible, otherwise try to preserve their previous protecting target if valid
        idle_group = "idle" if "idle" in group_ids else None
        for comp in components:
            if id(comp) in assigned_ids:
                continue
            # assign to idle if possible
            if idle_group:
                mark_assign(comp, idle_group)
            else:
                # try to preserve their current target if that protecting group exists
                if comp.target_id:
                    grp = f"protecting {comp.target_id}"
                    if grp in group_ids:
                        mark_assign(comp, grp)
                    else:
                        # last resort: assign to protecting group of highest if available
                        backup = f"protecting {highest.id}"
                        if backup in group_ids:
                            mark_assign(comp, backup)
                        else:
                            # cannot find a valid group; skip assignment (shouldn't happen in tests)
                            pass

        # Finally, perform the environment.assign_group calls exactly once per component according to our assignments
        for comp, grp in assignments:
            environment.assign_group(comp, grp)