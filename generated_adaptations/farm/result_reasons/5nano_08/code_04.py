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
            final_group = {d: "idle" for d in components}
            for d in components:
                environment.assign_group(d, final_group[d])
                self.prev_group[d] = final_group[d]
            return

        # Identify top (most threatened) field
        threatened_fields.sort(key=lambda f: f.threat_level, reverse=True)
        top_field = threatened_fields[0]
        top_group = f"protecting {top_field.id}"

        # Validate group name
        if top_group not in group_ids:
            # Fall back to idle if the group isn't valid
            final_group = {d: "idle" for d in components}
            for d in components:
                environment.assign_group(d, final_group[d])
                self.prev_group[d] = final_group[d]
            return

        top_center = field_center(top_field)

        # Top field handling
        capacity_top = getattr(top_field, 'drones_for_full_protection', len(components))
        current_top = [d for d in components if self.prev_group.get(d) == top_group]

        final_group = {}

        # If there are more drones currently protecting top than capacity, demote extras
        if len(current_top) > capacity_top:
            current_top.sort(key=lambda d: dist2_to_point(d, top_center))
            keep = current_top[:capacity_top]
            to_demote = current_top[capacity_top:]
            for d in to_demote:
                final_group[d] = "idle"
                self.prev_group[d] = "idle"
            current_top = keep

        # Ensure we have up to capacity_top drones for top_field by adding closest from others
        top_drones = list(current_top)
        if len(top_drones) < capacity_top:
            remaining = [d for d in components if d not in top_drones]
            remaining.sort(key=lambda d: dist2_to_point(d, top_center))
            needed = capacity_top - len(top_drones)
            top_drones.extend(remaining[:needed])

        for d in top_drones:
            final_group[d] = top_group

        # Track who has been assigned away from top so we don't reassign unnecessarily
        assigned_away_from_top = set(d for d in components if final_group.get(d) != top_group)

        # Other threatened fields
        other_fields = [f for f in threatened_fields if f.id != top_field.id]
        other_fields.sort(key=lambda f: f.threat_level, reverse=True)

        for f in other_fields:
            g = f"protecting {f.id}"
            if g not in group_ids:
                continue
            center = field_center(f)
            capacity = getattr(f, 'drones_for_full_protection', len(components))

            current = [d for d in components if final_group.get(d) == g]
            if len(current) > capacity:
                current.sort(key=lambda d: dist2_to_point(d, center))
                for d in current[capacity:]:
                    final_group[d] = "idle"
                    self.prev_group[d] = "idle"
                current = current[:capacity]

            assigned = list(current)
            if len(assigned) < capacity:
                # Candidates should avoid stealing top_group drones
                candidates = [d for d in components if final_group.get(d) not in (g, top_group)]
                candidates.sort(key=lambda d: dist2_to_point(d, center))
                need = capacity - len(assigned)
                for d in candidates[:need]:
                    final_group[d] = g
                    self.prev_group[d] = g
                    assigned.append(d)

        # Any remaining not in final_group -> idle
        for d in components:
            if d not in final_group:
                final_group[d] = "idle"

        # Ensure at least half engaged
        protection_set = [d for d in components if final_group.get(d) != "idle"]
        if len(protection_set) < len(components) // 2:
            # Try to move idle drones to top_group up to capacity
            top_current = [d for d in components if final_group.get(d) == top_group]
            top_cap = capacity_top
            if len(top_current) < top_cap:
                idle_candidates = [d for d in components if final_group.get(d) == "idle"]
                idle_candidates.sort(key=lambda d: dist2_to_point(d, top_center))
                for d in idle_candidates[:top_cap - len(top_current)]:
                    final_group[d] = top_group
                    top_current.append(d)

        # Assign to environment and update memory
        for d in components:
            grp = final_group.get(d, "idle")
            if grp not in group_ids:
                grp = "idle"
            environment.assign_group(d, grp)
            self.prev_group[d] = grp