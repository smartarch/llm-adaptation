from typing import List
import math
import abc

# Assuming the base class can be imported as described
# from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def _field_center(self, field) -> tuple:
        cx = (field.left + field.right) / 2.0
        cy = (field.top + field.bottom) / 2.0
        return (cx, cy)
    
    def _distance(self, p, q) -> float:
        dx = p.x - q[0]
        dy = p.y - q[1]
        return math.hypot(dx, dy)
    
    def assign_drones(self, components: List, environment, group_ids: List[str], step: int):
        # Determine the target field: the one with the highest threat > 0
        target_field = None
        max_threat = 0.0
        for field in environment.fields:
            if field.threat_level > max_threat:
                max_threat = field.threat_level
                target_field = field
        
        # Build list of valid groups for fields with threat > 0
        # (This is primarily for ensuring group_ids consistency)
        active_groups = []
        if target_field is not None and target_field.threat_level > 0:
            active_groups.append(f"protecting {target_field.id}")
        
        # If no threat fields, set all drones to idle
        if target_field is None or target_field.threat_level <= 0:
            for comp in components:
                environment.assign_group(comp, "idle")
            return
        
        # Compute how many drones are needed for full protection for the target field
        needed_total = target_field.drones_for_full_protection
        # Current number already protecting this field
        current_protecting = getattr(target_field, "protecting_drones", 0)
        need = int(needed_total - current_protecting)
        
        # If no more drones needed, keep existing protections
        if need <= 0:
            # Ensure all others are idle
            for comp in components:
                curr_group = None
                # If drone is already in protecting target_field, keep it; otherwise idle
                # We don't have a direct accessor for current group in this interface, so we set non-matching to idle
                environment.assign_group(comp, f"protecting {target_field.id}" if getattr(comp, "state", None) == "protecting" and getattr(comp, "target_id", None) == target_field.id else "idle")
            return
        
        # Gather candidate drones, sort by distance to field center
        field_center = self._field_center(target_field)
        candidates = []
        for comp in components:
            # Distance from drone's current location to field center
            pos = getattr(comp, "location", None)
            if pos is None:
                dist = float('inf')
            else:
                dist = self._distance(pos, field_center)
            candidates.append((dist, comp))
        candidates.sort(key=lambda x: x[0])
        
        # Assign the closest 'need' drones to protecting this field
        assigned = 0
        for dist, comp in candidates:
            if assigned >= need:
                break
            environment.assign_group(comp, f"protecting {target_field.id}")
            assigned += 1
        
        # The rest go to idle (or remain as is if already protecting? We assign idle to be explicit)
        for dist, comp in candidates[assigned:]:
            environment.assign_group(comp, "idle")