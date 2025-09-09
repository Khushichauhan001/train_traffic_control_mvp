from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class Block:
    id: str
    length_km: float
    max_speed_kmph: float
    direction: str = "bi"  # 'up', 'down', or 'bi'
    station: Optional[str] = None  # station id if this block is a station or has a loop
    loop_capacity: int = 1  # number of trains that can wait at the loop/station

@dataclass
class Section:
    id: str
    blocks: List[Block]
    headway_min: float = 3.0  # minimal minutes between consecutive trains entering same block

@dataclass
class Train:
    id: str
    priority: int  # lower number => higher priority
    max_speed_kmph: float
    dwell_min: float
    route: List[str]  # sequence of block ids to traverse
    direction: str  # 'up' or 'down'
    dep_time_min: float  # scheduled departure time (from first block)
    train_type: str = "UNKNOWN"  # EXPRESS, PASSENGER, FREIGHT, etc.

@dataclass
class TrainState:
    train: Train
    route_index: int = 0
    time_min: float = 0.0
    finished: bool = False
    delay_min: float = 0.0
    location: Optional[str] = None  # current block id

@dataclass
class ScheduleDecision:
    # simple record of planned entry times per train per block
    entries: Dict[str, Dict[str, float]] = field(default_factory=dict)

    def set_entry(self, train_id: str, block_id: str, t: float):
        self.entries.setdefault(train_id, {})[block_id] = t

    def get_entry(self, train_id: str, block_id: str) -> Optional[float]:
        return self.entries.get(train_id, {}).get(block_id)

