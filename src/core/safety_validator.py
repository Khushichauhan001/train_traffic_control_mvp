from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from .models import Train, Section, Block, ScheduleDecision
import logging

@dataclass
class SafetyViolation:
    """Represents a safety violation detected in the schedule"""
    train1_id: str
    train2_id: str
    block_id: str
    time: float
    violation_type: str
    severity: str  # 'critical', 'warning'
    message: str

class CollisionDetector:
    """
    Validates schedules for safety and detects potential collisions
    """
    
    def __init__(self, section: Section):
        self.section = section
        self.block_map = {b.id: b for b in section.blocks}
        self.logger = logging.getLogger(__name__)
    
    def validate_schedule(self, schedule: ScheduleDecision, trains: List[Train]) -> Tuple[bool, List[SafetyViolation]]:
        """
        Validates a schedule for safety violations.
        Returns (is_safe, list_of_violations)
        """
        violations = []
        
        # Check for same-block conflicts
        block_occupancy = self._build_occupancy_timeline(schedule, trains)
        
        for block_id, timeline in block_occupancy.items():
            # Sort by entry time
            sorted_timeline = sorted(timeline, key=lambda x: x[0])
            
            for i in range(len(sorted_timeline) - 1):
                entry1, exit1, train1_id = sorted_timeline[i]
                entry2, exit2, train2_id = sorted_timeline[i + 1]
                
                # Check if trains overlap in time
                if entry2 < exit1:
                    # Check if this is a critical collision or just insufficient headway
                    overlap_time = exit1 - entry2
                    
                    if overlap_time > 0:
                        violation = SafetyViolation(
                            train1_id=train1_id,
                            train2_id=train2_id,
                            block_id=block_id,
                            time=entry2,
                            violation_type="COLLISION_RISK",
                            severity="critical",
                            message=f"Trains {train1_id} and {train2_id} will occupy block {block_id} simultaneously!"
                        )
                        violations.append(violation)
                
                # Check headway
                headway = entry2 - exit1
                if headway < self.section.headway_min and headway >= 0:
                    violation = SafetyViolation(
                        train1_id=train1_id,
                        train2_id=train2_id,
                        block_id=block_id,
                        time=entry2,
                        violation_type="INSUFFICIENT_HEADWAY",
                        severity="warning",
                        message=f"Only {headway:.1f} min headway between {train1_id} and {train2_id} at block {block_id} (min: {self.section.headway_min} min)"
                    )
                    violations.append(violation)
        
        # Check for head-on collision risks (opposing trains in same block)
        violations.extend(self._check_head_on_collisions(schedule, trains))
        
        is_safe = not any(v.severity == "critical" for v in violations)
        return is_safe, violations
    
    def _build_occupancy_timeline(self, schedule: ScheduleDecision, trains: List[Train]) -> Dict[str, List[Tuple[float, float, str]]]:
        """
        Build timeline of block occupancy from schedule
        Returns dict: block_id -> list of (entry_time, exit_time, train_id)
        """
        block_occupancy = {}
        
        for train in trains:
            for block_id in train.route:
                entry_time = schedule.get_entry(train.id, block_id)
                if entry_time is not None:
                    block = self.block_map[block_id]
                    
                    # Calculate exit time
                    travel_time = (block.length_km / min(train.max_speed_kmph, block.max_speed_kmph)) * 60
                    dwell_time = train.dwell_min if block.station else 0
                    exit_time = entry_time + travel_time + dwell_time
                    
                    if block_id not in block_occupancy:
                        block_occupancy[block_id] = []
                    block_occupancy[block_id].append((entry_time, exit_time, train.id))
        
        return block_occupancy
    
    def _check_head_on_collisions(self, schedule: ScheduleDecision, trains: List[Train]) -> List[SafetyViolation]:
        """
        Check for potential head-on collisions (opposing trains meeting)
        """
        violations = []
        train_map = {t.id: t for t in trains}
        
        # Build timeline with direction info
        block_timeline = {}
        for train in trains:
            for block_id in train.route:
                entry_time = schedule.get_entry(train.id, block_id)
                if entry_time is not None:
                    block = self.block_map[block_id]
                    
                    # Skip if block allows bidirectional traffic or matches train direction
                    if block.direction == "bi" or block.direction == train.direction:
                        travel_time = (block.length_km / min(train.max_speed_kmph, block.max_speed_kmph)) * 60
                        dwell_time = train.dwell_min if block.station else 0
                        exit_time = entry_time + travel_time + dwell_time
                        
                        if block_id not in block_timeline:
                            block_timeline[block_id] = []
                        block_timeline[block_id].append((entry_time, exit_time, train.id, train.direction))
        
        # Check for opposing trains in same block
        for block_id, timeline in block_timeline.items():
            for i in range(len(timeline)):
                for j in range(i + 1, len(timeline)):
                    entry1, exit1, train1_id, dir1 = timeline[i]
                    entry2, exit2, train2_id, dir2 = timeline[j]
                    
                    # Check if trains overlap in time and have opposite directions
                    if dir1 != dir2 and not (exit1 <= entry2 or exit2 <= entry1):
                        # Check if block has station/loop for crossing
                        block = self.block_map[block_id]
                        if not block.station:
                            violation = SafetyViolation(
                                train1_id=train1_id,
                                train2_id=train2_id,
                                block_id=block_id,
                                time=max(entry1, entry2),
                                violation_type="HEAD_ON_COLLISION_RISK",
                                severity="critical",
                                message=f"Opposing trains {train1_id} (dir: {dir1}) and {train2_id} (dir: {dir2}) will meet at block {block_id} with no crossing facility!"
                            )
                            violations.append(violation)
        
        return violations
    
    def verify_block_clearance(self, block_id: str, time: float, schedule: ScheduleDecision, trains: List[Train]) -> bool:
        """
        Verify if a block is clear at a given time
        """
        for train in trains:
            if block_id in train.route:
                entry_time = schedule.get_entry(train.id, block_id)
                if entry_time is not None:
                    block = self.block_map[block_id]
                    travel_time = (block.length_km / min(train.max_speed_kmph, block.max_speed_kmph)) * 60
                    dwell_time = train.dwell_min if block.station else 0
                    exit_time = entry_time + travel_time + dwell_time
                    
                    if entry_time <= time < exit_time:
                        return False
        return True
