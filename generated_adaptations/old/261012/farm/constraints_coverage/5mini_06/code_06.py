from generated_adaptations.base_classes.farm import FarmAdaptation
import math
from math import ceil

class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, group_ids, step: int):
        """
        Allocate drones to protect fields according to:
        - Fully protect the highest-threat field using the closest drones (global selection).
        - Then, in descending threat order, fully protect other fields using closest remaining drones
          but never assign more drones to a field than its drones_for_full_protection.
        - If after that fewer than half of drones are protecting and more threatened fields remain,
          assign additional drones (closest-first) to reach at least half usage when possible.
        - Explicitly assign every drone each call. Do not assign to invalid group names.
        """
        def distance(comp, field):
            cx = (field.left + field.right) / 2.0
            cy = (field.top + field.bottom) / 2.0
            dx = getattr(comp.location, "x", 0.0) - cx
            dy = getattr(comp.location, "y", 0.0) - cy
            return math.hypot(dx, dy)

        total = len(components)
        if total == 0:
            return

        # Threatened fields (threat_level > 0)
        threatened = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not threatened:
            # Nothing to protect
            for comp in components:
                environment.assign_group(comp, "idle")
            return

        # Sort threatened fields by descending threat_level (higher first)
        threatened.sort(key=lambda f: f.threat_level, reverse=True)

        # Helper to get valid protecting group name for a field
        def protect_name(field):
            name = f"protecting {field.id}"
            return name if name in group_ids else None

        # Map comp -> whether assigned to protect (we'll build assignments)
        assigned_group = {}

        # 1) Secure the highest-threat field with the closest drones (global selection)
        highest = threatened[0]
        high_group = protect_name(highest)
        if high_group is None:
            # If protecting group invalid for highest, fall back to idle all
            for comp in components:
                environment.assign_group(comp, "idle")
            return

        try:
            required_high = max(0, int(highest.drones_for_full_protection))
        except Exception:
            required_high = 0

        # Sort all drones by distance to highest field center
        drones_sorted_by_high = sorted(components, key=lambda c: distance(c, highest))

        # Select exactly required_high drones (or all if not enough)
        selected_high = set(drones_sorted_by_high[:required_high])

        # Assign them to highest
        for c in selected_high:
            assigned_group[c] = high_group

        # Remaining drones after securing highest
        remaining = [c for c in components if c not in selected_high]

        # 2) Assign to other fields in descending threat order without overprotection
        # Keep track of how many protecting drones we have
        protecting_count = len(selected_high)

        # For each other field, try to fill up to its drones_for_full_protection using remaining drones.
        for field in threatened[1:]:
            if not remaining:
                break
            group = protect_name(field)
            if group is None:
                continue
            try:
                needed_full = max(0, int(field.drones_for_full_protection))
            except Exception:
                needed_full = 0
            if needed_full == 0:
                continue

            # Count remaining drones that are already committed to this field (moving_to_field or protecting)
            committed_here = [c for c in remaining
                              if getattr(c, "target_id", None) == field.id and getattr(c, "state", "") in ("moving_to_field", "protecting")]
            already_here = len(committed_here)

            need = max(0, needed_full - already_here)
            if need == 0:
                # ensure committed_here are assigned to this group
                for c in committed_here:
                    assigned_group[c] = group
                # remove them from remaining
                remaining = [c for c in remaining if c not in committed_here]
                protecting_count = len([c for c in assigned_group if assigned_group.get(c) != "idle"])
                continue

            # Select closest 'need' drones from remaining excluding the committed_here (they will be assigned too)
            # Sort remaining by distance to this field
            # Keep committed_here included as they count toward protection
            noncommitted = [c for c in remaining if c not in committed_here]
            noncommitted.sort(key=lambda c: distance(c, field))
            take = noncommitted[:need]
            # Assign committed_here and taken ones to this field
            for c in committed_here:
                assigned_group[c] = group
            for c in take:
                assigned_group[c] = group

            # Remove these drones from remaining
            used = set(committed_here) | set(take)
            remaining = [c for c in remaining if c not in used]
            protecting_count = len([c for c in assigned_group if assigned_group.get(c) != "idle"])

        # 3) If still fewer than half of drones are protecting, try to allocate remaining drones
        desired_protect = ceil(total / 2)
        if protecting_count < desired_protect and remaining:
            # Iterate threatened fields in descending threat and try to add more up to their full need
            for field in threatened:
                if not remaining or protecting_count >= desired_protect:
                    break
                group = protect_name(field)
                if group is None:
                    continue
                try:
                    full_need = max(0, int(field.drones_for_full_protection))
                except Exception:
                    full_need = 0
                if full_need == 0:
                    continue
                # Count how many already assigned to this field in assigned_group
                already_assigned_here = len([c for c, g in assigned_group.items() if g == group])
                can_add = max(0, full_need - already_assigned_here)
                if can_add == 0:
                    continue
                # Choose closest remaining drones to this field, but only as many as needed to reach desired_protect
                remaining.sort(key=lambda c: distance(c, field))
                to_take = min(can_add, len(remaining), desired_protect - protecting_count)
                take = remaining[:to_take]
                for c in take:
                    assigned_group[c] = group
                remaining = remaining[to_take:]
                protecting_count = len([c for c in assigned_group if assigned_group.get(c) != "idle"])

        # 4) Finalize: assign groups, others idle. Ensure we do not assign to invalid group names.
        for comp in components:
            group = assigned_group.get(comp, None)
            if group is None:
                environment.assign_group(comp, "idle")
            else:
                # safety check: only assign if group is in group_ids, else idle
                if group in group_ids:
                    environment.assign_group(comp, group)
                else:
                    environment.assign_group(comp, "idle")