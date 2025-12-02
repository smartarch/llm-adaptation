# Final adaptation strategy: deterministic, one-pass allocation that prioritizes the
# most threatened field. It preserves drones already protecting a field, and
# allocates the remaining idle drones to protect fields in threat order until
# each field reaches its full protection requirement. All drones are assigned exactly once.

from typing import List

from generated_adaptations.base_classes.farm import FarmAdaptation  # type: ignore

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components: List, environment, group_ids: List[str], step: int):
        # Gather fields with positive threat and sort by threat descending
        fields_with_threat = [
            f for f in environment.fields if getattr(f, "threat_level", 0.0) > 0.0
        ]
        fields_with_threat.sort(
            key=lambda f: float(getattr(f, "threat_level", 0.0)), reverse=True
        )

        # If no threats, idle every drone
        if not fields_with_threat:
            for c in components:
                environment.assign_group(c, "idle")
            return

        # Helper: how many drones are currently protecting each field
        current_protecting = {f.id: 0 for f in fields_with_threat}
        for c in components:
            if getattr(c, "state", None) == "protecting":
                tid = getattr(c, "target_id", None)
                if tid in current_protecting:
                    current_protecting[tid] += 1

        # Compute needs per field (threatened only)
        needs = {}
        for f in fields_with_threat:
            fid = f.id
            required = 0
            try:
                required = int(getattr(f, "drones_for_full_protection", 0))
            except Exception:
                required = 0
            needs[fid] = max(0, required - current_protecting.get(fid, 0))

        # Build assignment plan: one group per drone (ensure exactly one assignment per drone)
        desired_groups = [None] * len(components)

        # Step A: keep drones already protecting in their current group
        for i, c in enumerate(components):
            if getattr(c, "state", None) == "protecting":
                fid = getattr(c, "target_id", None)
                if fid is not None:
                    desired_groups[i] = f"protecting {fid}"
                else:
                    desired_groups[i] = "idle"

        # Build list of indices that are not yet assigned
        unassigned_indices = [i for i, g in enumerate(desired_groups) if g is None]

        # Step B: allocate unassigned drones to top fields in threat order
        for f in fields_with_threat:
            if needs.get(f.id, 0) <= 0:
                continue
            while needs[f.id] > 0 and unassigned_indices:
                idx = unassigned_indices.pop(0)
                desired_groups[idx] = f"protecting {f.id}"
                needs[f.id] -= 1

        # Step C: any remaining unassigned drones become idle
        for idx in unassigned_indices:
            desired_groups[idx] = "idle"

        # Apply assignments (one per drone)
        for c, grp in zip(components, desired_groups):
            environment.assign_group(c, grp)