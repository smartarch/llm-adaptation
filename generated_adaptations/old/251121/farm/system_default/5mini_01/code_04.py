from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    """
    Improved adaptation strategy:

    - Keep drones that are currently protecting (state == "protecting") at their field.
    - Treat drones that are "moving_to_field" as flexible (can be reassigned).
    - Always fully protect the field with the highest threat level first, using the closest available drones.
    - Then greedily try to fully protect additional fields by maximizing threat_level / additional_drones_needed,
      completing fields that give highest marginal benefit per drone.
    - Any remaining drones are sent to the closest threatened field (partial protection is better than idle).
    - All drones are explicitly assigned each step.
    """

    def assign_drones(self, components, environment, group_ids, step: int):
        def dist(drone, field):
            cx = (field.left + field.right) / 2.0
            cy = (field.top + field.bottom) / 2.0
            dx = getattr(drone.location, "x", 0.0) - cx
            dy = getattr(drone.location, "y", 0.0) - cy
            return math.hypot(dx, dy)

        idle_group = "idle"

        # Collect threatened fields (threat_level > 0)
        fields = [f for f in getattr(environment, "fields", []) if getattr(f, "threat_level", 0) > 0]
        if not fields:
            # No threats -> everyone idle
            for comp in components:
                if idle_group in group_ids:
                    environment.assign_group(comp, idle_group)
                else:
                    environment.assign_group(comp, group_ids[0] if group_ids else idle_group)
            return

        # Map protecting drones that are already protecting their target field
        protecting_by_field = {}
        for f in fields:
            protecting_by_field[f.id] = []
        for comp in components:
            if getattr(comp, "state", None) == "protecting" and getattr(comp, "target_id", None) in protecting_by_field:
                protecting_by_field[comp.target_id].append(comp)

        # Build a pool of drones that can be reassigned:
        # exclude drones that are protecting (we keep them where they are),
        # but include idle and moving_to_field drones.
        pool = [c for c in components if not (getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) in protecting_by_field)]

        # Select field with maximum threat_level (tie-break by id)
        fields_sorted_by_threat = sorted(fields, key=lambda f: (f.threat_level, str(f.id)), reverse=True)
        highest_field = fields_sorted_by_threat[0]
        protect_group_high = f"protecting {highest_field.id}"

        # Number required for full protection
        required_high = int(getattr(highest_field, "drones_for_full_protection", 0))
        # Count currently protecting drones at that field (those we will keep)
        committed_high = protecting_by_field.get(highest_field.id, [])
        selected_for_high = list(committed_high)

        # Need additional drones (from pool)
        need_high = max(0, required_high - len(selected_for_high))
        if need_high > 0:
            # sort pool by distance to highest_field and take closest need_high drones (or less if not enough)
            pool.sort(key=lambda c: dist(c, highest_field))
            to_take = pool[:need_high]
            selected_for_high.extend(to_take)
            # remove taken drones from pool
            pool = pool[need_high:]

        # Record assignments: mapping component -> group string
        assignments = {}

        # Assign all drones selected for highest field to its protecting group (if group exists)
        for comp in selected_for_high:
            if protect_group_high in group_ids:
                assignments[comp] = protect_group_high
            else:
                assignments[comp] = idle_group  # defensive fallback

        # Now attempt to fully protect other fields greedily by marginal benefit
        # Start with current protecting drones at their fields (they are already committed)
        # Build a dict of selected_protectors for other fields initially equal to protecting_by_field
        selected_by_field = {f.id: list(protecting_by_field.get(f.id, [])) for f in fields}
        # Highest field already handled; ensure its selected_by_field contains our selected_for_high
        selected_by_field[highest_field.id] = list(selected_for_high)

        # Pool currently contains drones available for allocation
        # Now process remaining fields: compute additional_needed and benefit metric threat / additional_needed
        other_fields = [f for f in fields if f.id != highest_field.id]
        # Greedy loop: while pool and there exists a field that can be improved
        while pool:
            best_field = None
            best_value = -1.0
            best_need = 0
            # Evaluate each field's marginal benefit per drone if we attempted to finish it
            for f in other_fields:
                required = int(getattr(f, "drones_for_full_protection", 0))
                already = len(selected_by_field.get(f.id, []))
                need = max(0, required - already)
                if need <= 0:
                    continue  # already fully protected
                # marginal benefit per drone; prefer finishing small-need high-threat fields
                value = (f.threat_level / need) if need > 0 else 0.0
                # tie-breaker: higher threat or smaller id
                if value > best_value:
                    best_value = value
                    best_field = f
                    best_need = need
            if best_field is None:
                break  # nothing more to do

            # Allocate up to best_need drones (closest ones) from pool
            pool.sort(key=lambda c: dist(c, best_field))
            take = pool[:best_need]
            if not take:
                break
            selected_by_field[best_field.id].extend(take)
            # Remove them from pool
            pool = pool[len(take):]

        # Any remaining drones: assign them to closest threatened field (partial protection), if any
        if pool:
            # sort fields by threat descending to break ties when distances are similar
            threatened_by_id = {f.id: f for f in fields}
            for comp in pool:
                # find closest threatened field
                closest = min(fields, key=lambda f: (dist(comp, f), -f.threat_level))
                selected_by_field.setdefault(closest.id, [])
                selected_by_field[closest.id].append(comp)
            pool = []

        # Build final assignments:
        # - For every field with selections, assign selected drones to that protecting group
        for f in fields:
            grp = f"protecting {f.id}"
            members = selected_by_field.get(f.id, [])
            for comp in members:
                # If this comp was already assigned (e.g., highest), it's okay to overwrite with same group
                if grp in group_ids:
                    assignments[comp] = grp
                else:
                    assignments[comp] = idle_group  # defensive fallback

        # Any component not assigned yet -> idle
        for comp in components:
            if comp not in assignments:
                if idle_group in group_ids:
                    assignments[comp] = idle_group
                else:
                    assignments[comp] = group_ids[0] if group_ids else idle_group

        # Finally, commit all assignments via environment.assign_group
        for comp, grp in assignments.items():
            environment.assign_group(comp, grp)