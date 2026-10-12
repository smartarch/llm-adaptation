from math import inf
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Remember previous assignment (drone -> group_id) to help persistence
        self.prev_group = {}

    def assign_drones(self, components, environment, group_ids, step: int):
        # Helper to compute field center
        def field_center(field):
            return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

        # Helper to compute squared distance between a drone and a point
        def dist2_to_point(drone, pt):
            loc = getattr(drone, 'location', None)
            if loc is None:
                return inf
            x = getattr(loc, 'x', None)
            y = getattr(loc, 'y', None)
            if x is None or y is None:
                return inf
            dx = x - pt[0]
            dy = y - pt[1]
            return dx * dx + dy * dy

        # Gather threat-enabled fields
        fields = list(environment.fields)
        threatened_fields = [f for f in fields if getattr(f, 'threat_level', 0) > 0]

        # If no threatened fields, idle all drones
        if not threatened_fields:
            for d in components:
                environment.assign_group(d, "idle")
                self.prev_group[d] = "idle"
            return

        # Identify top (most threatened) field
        threatened_fields.sort(key=lambda f: f.threat_level, reverse=True)
        top_field = threatened_fields[0]
        top_group = f"protecting {top_field.id}"

        # Validate group name
        if top_group not in group_ids:
            # Fall back to idle if the group isn't valid
            for d in components:
                environment.assign_group(d, "idle")
                self.prev_group[d] = "idle"
            return

        # Compute field centers
        top_center = field_center(top_field)

        # Drones currently protecting top field (from previous step)
        currently_top = [d for d in components if self.prev_group.get(d) == top_group]
        need_top = max(0, getattr(top_field, 'drones_for_full_protection', len(components)) - len(currently_top))

        # Sort currently_top by closeness to top field (to prefer the closest if we need to trim)
        if currently_top:
            currently_top.sort(key=lambda d: dist2_to_point(d, top_center))

        # Select exactly need_top drones for the top field, preferring closest among:
        top_drones = []

        # If we have some currently protecting top, keep the closest up to needed
        if currently_top:
            take = min(len(currently_top), need_top)
            top_drones.extend(currently_top[:take])

        # If we still need more to reach need_top, fill from remaining drones by distance to top
        if len(top_drones) < need_top:
            remaining_candidates = [d for d in components if d not in top_drones]
            remaining_candidates.sort(key=lambda d: dist2_to_point(d, top_center))
            to_take = need_top - len(top_drones)
            top_drones.extend(remaining_candidates[:to_take])

        # Ensure we do not exceed capacity for top_field
        if len(top_drones) > max(0, getattr(top_field, 'drones_for_full_protection', len(components))):
            top_drones = top_drones[:max(0, getattr(top_field, 'drones_for_full_protection', len(components)))]

        # Mark assignments for top group
        group_assignments = {}
        for d in top_drones:
            group_assignments[d] = top_group

        # Pool of drones that are not yet assigned to top_group
        unassigned = [d for d in components if d not in top_drones]

        # Prepare other threatened fields (excluding the top field)
        other_fields = [f for f in threatened_fields if f.id != top_field.id]
        other_fields.sort(key=lambda f: f.threat_level, reverse=True)

        # Allocate drones to other fields up to their full protection need
        for f in other_fields:
            other_group = f"protecting {f.id}"
            if other_group not in group_ids:
                continue  # skip if group not valid

            center = field_center(f)
            # Current drones protecting this field (from previous step)
            currently_here = [d for d in components if self.prev_group.get(d) == other_group]
            need_field = max(0, getattr(f, 'drones_for_full_protection', len(components)) - len(currently_here))

            if need_field <= 0:
                continue

            # Sort unassigned by distance to this field
            unassigned.sort(key=lambda d: dist2_to_point(d, center))

            taken = 0
            for d in list(unassigned):  # iterate over a copy as we mutate
                if taken >= need_field:
                    break
                # Assign this drone to the field
                group_assignments[d] = other_group
                unassigned.remove(d)
                taken += 1

        # Remaining drones (if any) go idle
        for d in unassigned:
            group_assignments[d] = "idle"

        # Optional: ensure at least half the drones are protecting
        total_drones = len(components)
        protected_now = [d for d in components if group_assignments.get(d, "idle") != "idle"]
        if len(protected_now) < total_drones // 2:
            # Try to bolster protection by moving closest idle drones to the top field, respecting capacity
            # Determine current top protection count
            current_top_count = len([d for d in components if group_assignments.get(d, None) == top_group])
            capacity_top = max(0, getattr(top_field, 'drones_for_full_protection', len(components)))
            # Compute how many more we can assign to top_field
            can_add_to_top = max(0, capacity_top - current_top_count)
            if can_add_to_top > 0:
                # idle candidates (not currently in top_group or other protection)
                idle_candidates = [d for d in components if group_assignments.get(d, "idle") == "idle"]
                idle_candidates.sort(key=lambda d: dist2_to_point(d, top_center))
                add = min(can_add_to_top, len(idle_candidates))
                for d in idle_candidates[:add]:
                    group_assignments[d] = top_group

        # Finally, push assignments to environment and remember them
        for d in components:
            grp = group_assignments.get(d, "idle")
            if grp not in group_ids:
                grp = "idle"
            environment.assign_group(d, grp)
            self.prev_group[d] = grp