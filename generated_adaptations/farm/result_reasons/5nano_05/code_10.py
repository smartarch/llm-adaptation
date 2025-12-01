from math import sqrt
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Persist across steps: map drone_id -> last_protected_field_id (string) or None
        self._last_target_by_drone = {}

    def assign_drones(self, components, environment, group_ids, step: int):
        # 1) Gather threatened fields (threat_level > 0)
        fields = list(getattr(environment, "fields", []))
        threatened_fields = [f for f in fields if getattr(f, "threat_level", 0) > 0]

        # If nothing is threatened, idle all drones and reset memory
        if not threatened_fields:
            for d in components:
                environment.assign_group(d, "idle")
            for d in components:
                self._last_target_by_drone[id(d)] = None
            return

        # 2) Compute field centers for distance calculations
        field_centers = {}
        for f in threatened_fields:
            cx = (f.left + f.right) / 2.0
            cy = (f.top  + f.bottom) / 2.0
            field_centers[f.id] = (cx, cy)

        # 3) Helper: determine current group for a drone (considers moving_to_field as protection)
        def current_group(d):
            st = getattr(d, "state", None)
            tid = getattr(d, "target_id", None)
            if st in ("protecting", "moving_to_field") and tid is not None:
                return f"protecting {tid}"
            return "idle"

        # 4) Start with the current assignment as the baseline
        final_group = {d: current_group(d) for d in components}

        # 5) Sort threatened fields by threat descending
        threatened_sorted = sorted(
            threatened_fields,
            key=lambda ff: getattr(ff, "threat_level", 0),
            reverse=True
        )

        # Helper to fill a field to full protection with prioritized candidates
        def fill_field_to_full(field):
            field_id = field.id
            grp = f"protecting {field_id}"
            current_protectors = sum(1 for d in components if final_group.get(d) == grp)
            needed = int(getattr(field, "drones_for_full_protection", 0)) - current_protectors
            if needed <= 0:
                return
            cx, cy = field_centers[field_id]

            # Build candidates not currently protecting this field
            candidates = []
            for d in components:
                if final_group.get(d) == grp:
                    continue
                loc = getattr(d, "location", None)
                if loc is None:
                    dist = float("inf")
                else:
                    dx = getattr(loc, "x", 0.0) - cx
                    dy = getattr(loc, "y", 0.0) - cy
                    dist = sqrt(dx*dx + dy*dy)
                # arrival time to top field
                if getattr(d, "state", None) in ("moving_to_field", "protecting") and getattr(d, "target_id", None) == field_id:
                    arrival = 0.0
                else:
                    arrival = dist / 2.0  # speed = 2
                # memory bias: prefer drones that previously protected this field
                last_match = (self._last_target_by_drone.get(id(d)) == field_id)
                candidates.append((0 if last_match else 1, arrival, dist, d))
            candidates.sort(key=lambda t: (t[0], t[1], t[2]))
            for _, _, _, d in candidates[:max(0, needed)]:
                final_group[d] = grp

        # Phase 1: top field
        top_field = threatened_sorted[0]
        fill_field_to_full(top_field)

        # Phase 2: bolstering other fields if beneficial
        total = len(components)
        half = (total + 1) // 2
        current_protectors = sum(1 for d in components if final_group.get(d, "idle").startswith("protecting "))
        if current_protectors < half:
            for f in threatened_sorted[1:]:
                if current_protectors >= half:
                    break
                grp = f"protecting {f.id}"
                current = sum(1 for d in components if final_group.get(d) == grp)
                if current >= int(getattr(f, "drones_for_full_protection", 0)):
                    continue
                cx, cy = field_centers[f.id]
                candidates = []
                for d in components:
                    if final_group.get(d) == grp:
                        continue
                    loc = getattr(d, "location", None)
                    dist = float("inf") if loc is None else sqrt((getattr(loc,"x",0.0)-cx)**2 + (getattr(loc,"y",0.0)-cy)**2)
                    arr = 0.0 if (getattr(d, "state", None) in ("moving_to_field","protecting") and getattr(d, "target_id", None) == f.id) else dist / 2.0
                    memory_match = (self._last_target_by_drone.get(id(d)) == f.id)
                    candidates.append((0 if memory_match else 1, arr, dist, d))
                candidates.sort(key=lambda t: (t[0], t[1], t[2]))
                needed = int(getattr(f, "drones_for_full_protection", 0)) - current
                if needed <= 0:
                    continue
                for _, _, _, d in candidates[:needed]:
                    final_group[d] = grp
                    current_protectors += 1
                    if current_protectors >= half:
                        break

        # 3 memory update
        for d in components:
            g = final_group.get(d, "idle")
            if isinstance(g, str) and g.startswith("protecting "):
                fid = g.split(" ", 1)[1]
                self._last_target_by_drone[id(d)] = fid
            else:
                self._last_target_by_drone[id(d)] = None

        for d in components:
            environment.assign_group(d, final_group.get(d, "idle"))