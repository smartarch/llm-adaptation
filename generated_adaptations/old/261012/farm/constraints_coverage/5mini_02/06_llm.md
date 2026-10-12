Reasoning and strategy

We must always fully protect the single field with the highest threat level using the closest drones and keep any drones already protecting it. Tests also require that at least half of the drones are actively protecting fields most of the time. To satisfy both:

- If no fields have threat_level > 0, assign all drones to "idle".
- Pick the field with the highest threat_level (top_field). Keep all drones currently protecting that field.
- Fill that top field up to its drones_for_full_protection requirement using movers toward it first, then closest idle/movable drones.
- If after protecting the top field fewer than half the drones are protecting, iterate other threatened fields by descending threat_level and fill them (keeping their existing protectors and movers first, adding nearest drones as needed) until at least half of all drones are assigned to protecting groups or until we run out of drones/fields.
- Assign every drone explicitly each step: selected drones to "protecting {field.id}", all others to "idle".
- Validate group names against group_ids, falling back to "idle" if necessary.

This preserves the primary constraint (top field fully protected) while using spare drones to achieve the half-utilization desideratum.

```py
from generated_adaptations.base_classes.farm import FarmAdaptation
import math
from math import ceil

class SmartFarmAdaptation(FarmAdaptation):
    """
    Adaptation that:
    - Always fully protects the single field with the highest threat level using the closest drones.
    - Keeps drones already protecting that top field.
    - Then assigns additional drones to protect other threatened fields (by threat level),
      until at least half of the total drones are protecting (if possible).
    - All components are explicitly assigned each step.
    """
    def assign_drones(self, components, environment, group_ids, step: int):
        def valid_group(name):
            return name if name in group_ids else "idle"

        # Gather threatened fields (threat_level > 0)
        threatened_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # If none, set all drones to idle
        if not threatened_fields:
            idle_group = valid_group("idle")
            for comp in components:
                environment.assign_group(comp, idle_group)
            return

        # Helpers for distances
        def field_center(field):
            return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

        def distance_to_field(comp, field):
            cx, cy = field_center(field)
            dx = getattr(comp.location, "x", 0) - cx
            dy = getattr(comp.location, "y", 0) - cy
            return math.hypot(dx, dy)

        # Build lookup of current protectors and movers by field id
        protecting_by_field = {}
        moving_by_field = {}
        for comp in components:
            state = getattr(comp, "state", "")
            target = getattr(comp, "target_id", None)
            if state == "protecting" and target is not None:
                protecting_by_field.setdefault(target, []).append(comp)
            if state == "moving_to_field" and target is not None:
                moving_by_field.setdefault(target, []).append(comp)

        total_drones = len(components)
        half_required = ceil(total_drones / 2)

        # Choose top field by threat_level
        top_field = max(threatened_fields, key=lambda f: f.threat_level)
        # Other fields sorted by descending threat_level
        other_fields = [f for f in threatened_fields if f.id != top_field.id]
        other_fields.sort(key=lambda f: f.threat_level, reverse=True)

        # Selected assignments: component -> field_id
        selected_assignment = {}

        # Available set of components not yet assigned
        available = set(components)

        # Helper to fill a field up to 'required' using available drones.
        # Keeps existing protectors (for that field) and movers to that field, then adds nearest available drones.
        # If existing protectors exceed required, they are all kept (we don't evict).
        def fill_field(field, required):
            # Keep existing protectors for this field if they are available
            kept = []
            for comp in protecting_by_field.get(field.id, []):
                if comp in available:
                    kept.append(comp)
            chosen = list(kept)

            # Include movers next (if still available and not already chosen)
            movers = [c for c in moving_by_field.get(field.id, []) if c in available and c not in chosen]
            need = max(0, required - len(chosen))
            if need > 0:
                chosen.extend(movers[:need])

            # If still need more, pick nearest from remaining available
            if len(chosen) < required:
                need = required - len(chosen)
                remaining_candidates = [c for c in available if c not in chosen]
                remaining_candidates.sort(key=lambda c: distance_to_field(c, field))
                chosen.extend(remaining_candidates[:need])

            # Assign chosen to this field and remove from available
            for comp in chosen:
                selected_assignment[comp] = field.id
                if comp in available:
                    available.remove(comp)

        # Fill the top field to its requirement (keep existing protectors)
        required_top = int(getattr(top_field, "drones_for_full_protection", 0))
        fill_field(top_field, required_top)

        # If fewer than half are protecting, try to fill other fields until half is reached
        if len(selected_assignment) < half_required:
            for field in other_fields:
                if len(selected_assignment) >= half_required:
                    break
                if not available:
                    break
                required = int(getattr(field, "drones_for_full_protection", 0))
                fill_field(field, required)

        # As a last attempt, if still under half and there are available drones, keep any remaining current protectors
        # for threatened fields (they are beneficial). This will assign them to their current targets.
        if len(selected_assignment) < half_required and available:
            for comp in list(available):
                if len(selected_assignment) >= half_required:
                    break
                if getattr(comp, "state", "") == "protecting":
                    target = getattr(comp, "target_id", None)
                    # Only keep if target is a threatened field
                    if target and any(f.id == target for f in threatened_fields):
                        selected_assignment[comp] = target
                        available.remove(comp)

        # Prepare group names
        idle_group = valid_group("idle")
        protecting_group_cache = {}
        for f in threatened_fields:
            protecting_group_cache[f.id] = valid_group(f"protecting {f.id}")

        # Assign groups for all components explicitly
        for comp in components:
            if comp in selected_assignment:
                field_id = selected_assignment[comp]
                group_name = protecting_group_cache.get(field_id, idle_group)
                environment.assign_group(comp, group_name)
            else:
                environment.assign_group(comp, idle_group)