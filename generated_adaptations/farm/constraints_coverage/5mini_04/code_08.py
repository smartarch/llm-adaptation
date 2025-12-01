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

        # gather threatened fields
        threatened = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not threatened:
            idle_group = "idle" if "idle" in group_ids else None
            for comp in components:
                if idle_group:
                    environment.assign_group(comp, idle_group)
            return

        threatened.sort(key=lambda f: (-f.threat_level, str(getattr(f, "id", ""))))
        highest = threatened[0]
        highest_group = f"protecting {highest.id}"

        # Bookkeeping for assignments
        assignments = []
        assigned_ids = set()

        def mark_assign(comp, grp):
            cid = id(comp)
            if cid in assigned_ids:
                return False
            assigned_ids.add(cid)
            assignments.append((comp, grp))
            return True

        # 1) Fully protect highest using closest drones (or keep committed ones if already enough)
        required_highest = int(getattr(highest, "drones_for_full_protection", 0))
        if required_highest > 0 and highest_group in group_ids:
            # find all components not yet assigned
            unassigned = [c for c in components if id(c) not in assigned_ids]
            # find committed to highest among unassigned
            committed_to_highest = [c for c in unassigned if getattr(c, "target_id", None) == highest.id]
            if len(committed_to_highest) >= required_highest:
                # keep the closest committed subset
                cx, cy = field_center(highest)
                committed_to_highest.sort(key=lambda c: dist2(c.location, cx, cy))
                for c in committed_to_highest[:required_highest]:
                    mark_assign(c, highest_group)
            else:
                # pick required_highest closest drones among all unassigned
                cx, cy = field_center(highest)
                candidates = sorted(unassigned, key=lambda c: dist2(c.location, cx, cy))
                for c in candidates[:required_highest]:
                    mark_assign(c, highest_group)

        # Update unassigned list after highest assignment
        unassigned = [c for c in components if id(c) not in assigned_ids]

        # Helper to get counts for a field including committed that are still unassigned
        def count_committed_unassigned(field):
            return [c for c in unassigned if getattr(c, "target_id", None) == field.id]

        # 2) Try to fully protect other fields in descending threat order, using committed drones first
        for f in threatened[1:]:
            group_name = f"protecting {f.id}"
            if group_name not in group_ids:
                continue
            required = int(getattr(f, "drones_for_full_protection", 0))
            if required <= 0:
                continue
            # recompute unassigned
            unassigned = [c for c in components if id(c) not in assigned_ids]
            if not unassigned:
                break
            committed = count_committed_unassigned(f)
            committed_count = len(committed)
            need = max(0, required - committed_count)
            # can we supply 'need' extra drones from unassigned excluding committed?
            others = [c for c in unassigned if getattr(c, "target_id", None) != f.id]
            if need == 0:
                # already enough committed -> keep committed (assign them)
                # assign all committed (or up to required? we keep committed ones)
                cx, cy = field_center(f)
                committed.sort(key=lambda c: dist2(c.location, cx, cy))
                for c in committed:
                    mark_assign(c, group_name)
            elif len(others) >= need:
                # we can fully protect this field: assign committed + closest others
                cx, cy = field_center(f)
                # assign committed first
                committed.sort(key=lambda c: dist2(c.location, cx, cy))
                for c in committed:
                    mark_assign(c, group_name)
                # assign closest 'need' from others
                others.sort(key=lambda c: dist2(c.location, cx, cy))
                for c in others[:need]:
                    mark_assign(c, group_name)
            else:
                # cannot fully protect this field with available drones -> skip for now (do not assign partials yet)
                continue
            # update unassigned for next field
            unassigned = [c for c in components if id(c) not in assigned_ids]

        # Count how many protecting assigned so far
        protect_count = sum(1 for _, g in assignments if g.startswith("protecting "))

        # 3) If we haven't reached the minimum protection usage (half the drones), try to reach it.
        # Prefer to fully protect additional fields if possible; otherwise concentrate remaining drones to a single field.
        if protect_count < min_protect_needed:
            # recompute unassigned
            unassigned = [c for c in components if id(c) not in assigned_ids]
            # First pass: try to fully protect any remaining fields (same procedure but now with updated unassigned)
            for f in threatened:
                if protect_count >= min_protect_needed:
                    break
                group_name = f"protecting {f.id}"
                if group_name not in group_ids:
                    continue
                required = int(getattr(f, "drones_for_full_protection", 0))
                if required <= 0:
                    continue
                # count current assigned to this field
                curr_assigned = sum(1 for _, g in assignments if g == group_name)
                if curr_assigned >= required:
                    continue
                # count committed unassigned to this field
                unassigned = [c for c in components if id(c) not in assigned_ids]
                committed = [c for c in unassigned if getattr(c, "target_id", None) == f.id]
                committed_count = len(committed)
                need = max(0, required - committed_count)
                others = [c for c in unassigned if getattr(c, "target_id", None) != f.id]
                if need == 0 and committed_count > 0:
                    # assign committed
                    cx, cy = field_center(f)
                    committed.sort(key=lambda c: dist2(c.location, cx, cy))
                    for c in committed:
                        if mark_assign(c, group_name):
                            protect_count += 1
                elif len(others) >= need and need > 0:
                    # assign committed + others
                    cx, cy = field_center(f)
                    committed.sort(key=lambda c: dist2(c.location, cx, cy))
                    for c in committed:
                        if mark_assign(c, group_name):
                            protect_count += 1
                    others.sort(key=lambda c: dist2(c.location, cx, cy))
                    for c in others[:need]:
                        if mark_assign(c, group_name):
                            protect_count += 1
                # update unassigned
                unassigned = [c for c in components if id(c) not in assigned_ids]

            # If still below threshold, concentrate remaining unassigned drones onto the single best field
            if protect_count < min_protect_needed and unassigned:
                # choose best field: highest threat that has a protecting group
                best_field = None
                for f in threatened:
                    if f"protecting {f.id}" in group_ids:
                        best_field = f
                        break
                if best_field is not None:
                    grp = f"protecting {best_field.id}"
                    # assign all remaining unassigned to that grp (concentrate)
                    # However, avoid reassigning those already assigned elsewhere
                    for c in list(unassigned):
                        if mark_assign(c, grp):
                            protect_count += 1
                    unassigned = [c for c in components if id(c) not in assigned_ids]

        # 4) Any still-unassigned drones -> idle (if exists) or try preserve current protecting group
        idle_group = "idle" if "idle" in group_ids else None
        for c in components:
            if id(c) in assigned_ids:
                continue
            if idle_group:
                mark_assign(c, idle_group)
            else:
                # try preserve their current protecting group
                if c.target_id:
                    grp = f"protecting {c.target_id}"
                    if grp in group_ids:
                        mark_assign(c, grp)
                    else:
                        # fallback to highest protecting if exists
                        if highest_group in group_ids:
                            mark_assign(c, highest_group)
                        else:
                            # as last resort assign to any protecting group available
                            for f in threatened:
                                grp2 = f"protecting {f.id}"
                                if grp2 in group_ids:
                                    mark_assign(c, grp2)
                                    break

        # 5) Perform assignments
        for comp, grp in assignments:
            environment.assign_group(comp, grp)