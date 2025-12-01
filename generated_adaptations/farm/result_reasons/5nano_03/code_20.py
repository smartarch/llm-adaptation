import math

# Assume the base class FarmAdaptation is available from the given import path
# from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Memory: map from drone id to last assigned group
        self._prev_group_by_drone = {}

    def assign_drones(self, components, environment, group_ids, step: int):
        n = len(components)
        if n == 0:
            return

        # Helpers
        def field_center(field):
            return (
                (getattr(field, 'left', 0) + getattr(field, 'right', 0)) / 2.0,
                (getattr(field, 'top', 0) + getattr(field, 'bottom', 0)) / 2.0,
            )

        def dist_to_point(drone, x, y):
            loc = getattr(drone, "location", None)
            if not loc or not hasattr(loc, "x") or not hasattr(loc, "y"):
                return float("inf")
            return math.hypot(loc.x - x, loc.y - y)

        # Gather threatened fields
        threatened = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # If no threats, idle all drones
        if not threatened:
            for d in components:
                grp = "idle"
                if grp not in group_ids:
                    grp = "idle"
                environment.assign_group(d, grp)
                self._prev_group_by_drone[id(d)] = grp
            return

        # Sort threatened fields by threat level (desc)
        threatened.sort(key=lambda f: getattr(f, "threat_level", 0), reverse=True)
        top_field = threatened[0]
        top_group = f"protecting {top_field.id}"
        top_required = int(getattr(top_field, "drones_for_full_protection", 0))
        can_protect_top = (top_group in group_ids) and top_required > 0

        top_center = field_center(top_field)

        # Build initial final_group map (index -> group_id) based on current environment
        final_group = []
        for i, d in enumerate(components):
            grp = "idle"
            st = getattr(d, "state", None)
            if st == "protecting" and getattr(d, "target_id", None) is not None:
                t = d.target_id
                g = f"protecting {t}"
                grp = g if g in group_ids else "idle"
            final_group.append(grp)

        # Stage 1: Top field protection
        top_current = [i for i, g in enumerate(final_group) if g == top_group]

        if can_protect_top:
            # If too many protectors, move farthest ones to idle
            if len(top_current) > top_required:
                top_current.sort(key=lambda idx: dist_to_point(components[idx], top_center[0], top_center[1]), reverse=True)
                to_remove = top_current[top_required:]
                for idx in to_remove:
                    final_group[idx] = "idle"
                    self._prev_group_by_drone[id(components[idx])] = "idle"
                top_current = top_current[:top_required]

            # Assign remaining current_top protectors to top_group
            for idx in top_current:
                final_group[idx] = top_group
                self._prev_group_by_drone[id(components[idx])] = top_group

            # Fill to reach top_required with closest drones not yet on top
            if len(top_current) < top_required:
                need = top_required - len(top_current)
                pool = [i for i in range(n) if final_group[i] != top_group]
                pool.sort(key=lambda i: (
                    self._prev_group_by_drone.get(id(components[i]), None) != top_group,
                    dist_to_point(components[i], top_center[0], top_center[1])
                ))
                for idx in pool[:need]:
                    final_group[idx] = top_group
                    self._prev_group_by_drone[id(components[idx])] = top_group
                    top_current.append(idx)

        # Stage 2: Secondary fields
        secondary = threatened[1:]
        secondary.sort(key=lambda f: getattr(f, "threat_level", 0), reverse=True)

        for f in secondary:
            grp = f"protecting {f.id}"
            if grp not in group_ids:
                continue
            cx, cy = field_center(f)

            # Current protectors for this field
            current = [i for i, g in enumerate(final_group) if g == grp]
            required = int(getattr(f, "drones_for_full_protection", 0))
            need = max(0, required - len(current))
            if need <= 0:
                continue

            pool = [i for i in range(n) if final_group[i] != grp]
            pool.sort(key=lambda i: (
                self._prev_group_by_drone.get(id(components[i]), None) != grp,
                dist_to_point(components[i], cx, cy)
            ))
            for idx in pool[:need]:
                final_group[idx] = grp
                self._prev_group_by_drone[id(components[idx])] = grp

        # Stage 3: Ensure at least half are protecting when threats exist
        protecting_now = [i for i, g in enumerate(final_group) if g != "idle"]
        min_protect = int(math.ceil(n / 2.0))
        if len(protecting_now) < min_protect:
            # First, try to fill top field to capacity if possible
            if can_protect_top and top_required > 0:
                top_current = [i for i, g in enumerate(final_group) if g == top_group]
                top_needed = max(0, top_required - len(top_current))
                if top_needed > 0:
                    candidates = [i for i in range(n) if final_group[i] != top_group]
                    candidates.sort(key=lambda i: dist_to_point(components[i], top_center[0], top_center[1]))
                    add = min(top_needed, len(candidates))
                    for idx in candidates[:add]:
                        final_group[idx] = top_group
                        self._prev_group_by_drone[id(components[idx])] = top_group
                        protecting_now.append(idx)

            # If still not enough, fill secondary fields using remaining drones
            if len([i for i in range(n) if final_group[i] != "idle"]) < min_protect:
                # Fill from non-top drones into secondary fields with available capacity
                for f in secondary:
                    grp = f"protecting {f.id}"
                    if grp not in group_ids:
                        continue
                    center_xy = field_center(f)
                    required = int(getattr(f, "drones_for_full_protection", 0))
                    current = [i for i, g in enumerate(final_group) if g == grp]
                    need = max(0, required - len(current))
                    if need <= 0:
                        continue
                    pool = [i for i in range(n) if final_group[i] != grp and final_group[i] != top_group]
                    pool.sort(key=lambda i: (
                        self._prev_group_by_drone.get(id(components[i]), None) != grp,
                        dist_to_point(components[i], center_xy[0], center_xy[1])
                    ))
                    for idx in pool[:need]:
                        final_group[idx] = grp
                        self._prev_group_by_drone[id(components[idx])] = grp
                        protecting_now.append(idx)
                        if len(protecting_now) >= min_protect:
                            break

        # Stage 4: Finalize assignments
        for i, d in enumerate(components):
            grp = final_group[i]
            if grp not in group_ids:
                last = self._prev_group_by_drone.get(id(d))
                grp = last if last in group_ids else "idle"
            environment.assign_group(d, grp)
            self._prev_group_by_drone[id(d)] = grp