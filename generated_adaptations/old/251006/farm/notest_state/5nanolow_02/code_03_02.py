# Improved adaptation strategy (multi-field prioritized protection with proximity-based allocation)

from typing import List
import abc
import math

try:
    from generated_adaptations.base_classes.farm import FarmAdaptation
except Exception:
    class FarmAdaptation(abc.ABC):
        def __init__(self, **kwargs):
            pass

        @abc.abstractmethod
        def assign_drones(self, components, environment, group_ids, step: int):
            pass


class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _center_of_field(self, field):
        left = getattr(field, "left", 0)
        top = getattr(field, "top", 0)
        right = getattr(field, "right", 0)
        bottom = getattr(field, "bottom", 0)
        cx = (left + right) / 2.0
        cy = (top + bottom) / 2.0
        return cx, cy

    def assign_drones(self, components, environment, group_ids, step: int):
        # Gather threat fields
        fields = getattr(environment, "fields", []) or []
        threat_fields = [f for f in fields if getattr(f, "threat_level", 0) > 0]

        # If no threat, all idle
        if not threat_fields:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Sort fields by threat level (desc)
        threat_fields.sort(key=lambda f: getattr(f, "threat_level", 0), reverse=True)

        # Build current protection mapping: field_id -> list of drones currently protecting it
        field_current = {}
        for f in threat_fields:
            fid = getattr(f, "id", None)
            if fid is None:
                continue
            current = [d for d in components if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == fid]
            field_current[fid] = current

        # Determine available drones to allocate: idle + moving_to_field heading to threat fields
        available = []
        for d in components:
            if getattr(d, "state", None) == "protecting":
                # Do not reallocate already-protecting drones in this pass
                continue
            if getattr(d, "state", None) == "moving_to_field":
                target = getattr(d, "target_id", None)
                # If heading to any threat field, consider as potentially useful
                if target in [getattr(ff, "id", None) for ff in threat_fields]:
                    available.append(d)
                else:
                    available.append(d)
            else:
                # idle
                available.append(d)

        # Helper to compute distance from drone to field center
        def dist_to_field(drone, field):
            cx, cy = self._center_of_field(field)
            dx = getattr(drone.location, "x", 0) - cx
            dy = getattr(drone.location, "y", 0) - cy
            return (dx * dx + dy * dy) ** 0.5

        # Track which drones we allocate in this step
        allocated_ids = set()

        # For each threat field in priority order, allocate to full protection if needed
        for field in threat_fields:
            fid = getattr(field, "id", None)
            if fid is None:
                continue
            current = field_current.get(fid, [])
            current_count = len(current)
            required = getattr(field, "drones_for_full_protection", 0)

            if current_count >= max(0, required):
                # Already fully protected; ensure group consistency
                for d in current:
                    environment.assign_group(d, f"protecting {fid}")
                    allocated_ids.add(id(d))
                continue

            need = max(0, required - current_count)

            # Pick closest available drones
            if need > 0:
                # Build candidate list with distance
                candidates = []
                for d in available:
                    # Skip drones already allocated
                    if id(d) in allocated_ids:
                        continue
                    dth = dist_to_field(d, field)
                    candidates.append((dth, d))
                candidates.sort(key=lambda t: t[0])

                for _, d in candidates:
                    if need <= 0:
                        break
                    environment.assign_group(d, f"protecting {fid}")
                    allocated_ids.add(id(d))
                    need -= 1

        # After processing, assign remaining drones to idle
        for d in components:
            if id(d) in allocated_ids:
                continue
            environment.assign_group(d, "idle")