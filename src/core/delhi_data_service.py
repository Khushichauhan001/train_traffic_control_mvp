from typing import List, Dict, Tuple
from datetime import datetime, timedelta
import random
from .models import Train, Section, Block
import requests
import json

class DelhiStationDataService:
    """
    Service to provide real-time Delhi station data and train information
    """
    
    def __init__(self):
        # Real Delhi Metro/Railway stations and routes
        self.delhi_stations = {
            "NDLS": {"name": "New Delhi", "type": "major", "platforms": 16},
            "DLI": {"name": "Delhi Junction", "type": "major", "platforms": 12},
            "DSA": {"name": "Delhi Shahdara", "type": "junction", "platforms": 6},
            "DKZ": {"name": "Delhi Kishan Ganj", "type": "local", "platforms": 4},
            "SZM": {"name": "Subzi Mandi", "type": "junction", "platforms": 8},
            "TKJ": {"name": "Tilak Bridge", "type": "local", "platforms": 4},
            "CSB": {"name": "Shivaji Bridge", "type": "local", "platforms": 3},
            "ANVT": {"name": "Anand Vihar Terminal", "type": "terminal", "platforms": 10},
            "GZB": {"name": "Ghaziabad", "type": "major", "platforms": 8},
            "MTC": {"name": "Meerut City", "type": "junction", "platforms": 6}
        }
        
        # Real train types and their characteristics
        self.train_types = {
            "RAJDHANI": {"priority": 1, "max_speed": 130, "dwell_time": 2},
            "SHATABDI": {"priority": 1, "max_speed": 140, "dwell_time": 2},
            "EXPRESS": {"priority": 2, "max_speed": 110, "dwell_time": 3},
            "SUPERFAST": {"priority": 2, "max_speed": 100, "dwell_time": 3},
            "PASSENGER": {"priority": 3, "max_speed": 75, "dwell_time": 5},
            "LOCAL": {"priority": 4, "max_speed": 60, "dwell_time": 2},
            "FREIGHT": {"priority": 5, "max_speed": 50, "dwell_time": 0}
        }
        
        # Popular Delhi routes
        self.popular_routes = [
            ["NDLS", "DLI", "DSA", "ANVT"],
            ["NDLS", "SZM", "DSA", "GZB"],
            ["DLI", "TKJ", "CSB", "ANVT"],
            ["NDLS", "DKZ", "DSA", "MTC"],
            ["ANVT", "GZB", "MTC"],
            ["DLI", "SZM", "DSA"]
        ]

    def get_real_time_data(self) -> Dict:
        """
        Simulate fetching real-time data from Delhi stations
        In production, this would call actual APIs like IRCTC or Indian Railways
        """
        current_time = datetime.now()
        
        # Simulate API response with realistic data
        real_time_data = {
            "timestamp": current_time.isoformat(),
            "station_status": self._get_station_status(),
            "live_trains": self._get_live_trains(),
            "track_occupancy": self._get_track_occupancy(),
            "weather_conditions": self._get_weather_conditions(),
            "system_alerts": self._get_system_alerts()
        }
        
        return real_time_data

    def _get_station_status(self) -> Dict:
        """Get current status of Delhi stations"""
        station_status = {}
        for station_code, info in self.delhi_stations.items():
            status = random.choice(["NORMAL", "CROWDED", "DELAYED", "MAINTENANCE"])
            occupied_platforms = random.randint(0, info["platforms"])
            
            station_status[station_code] = {
                "name": info["name"],
                "status": status,
                "total_platforms": info["platforms"],
                "occupied_platforms": occupied_platforms,
                "passenger_load": random.choice(["LOW", "MEDIUM", "HIGH"]),
                "last_updated": datetime.now().strftime("%H:%M:%S")
            }
        
        return station_status

    def _get_live_trains(self) -> List[Dict]:
        """Get live train information"""
        live_trains = []
        train_numbers = [12001, 12002, 12951, 12952, 12801, 12802, 14011, 14012]
        
        for i, train_num in enumerate(train_numbers):
            train_type = random.choice(list(self.train_types.keys()))
            route = random.choice(self.popular_routes)
            direction = "UP" if i % 2 == 0 else "DOWN"
            
            if direction == "DOWN":
                route = route[::-1]  # Reverse route for down trains
            
            current_position = random.choice(route)
            delay = random.randint(-5, 30)  # -5 to +30 minutes
            
            live_trains.append({
                "train_number": f"{train_type[:3]}-{train_num}",
                "train_name": f"{train_type} Express",
                "type": train_type,
                "route": route,
                "direction": direction,
                "current_station": current_position,
                "next_station": self._get_next_station(route, current_position),
                "delay_minutes": delay,
                "status": "RUNNING" if delay < 15 else "DELAYED",
                "estimated_arrival": self._calculate_eta(delay),
                "passenger_load": random.randint(60, 95),
                "last_reported": datetime.now().strftime("%H:%M:%S")
            })
        
        return live_trains

    def _get_track_occupancy(self) -> Dict:
        """Get current track occupancy information"""
        tracks = {}
        for station_code in self.delhi_stations.keys():
            for track_num in range(1, 5):  # 4 tracks per station
                track_id = f"{station_code}-T{track_num}"
                is_occupied = random.choice([True, False, False])  # 33% occupied
                
                tracks[track_id] = {
                    "occupied": is_occupied,
                    "train_id": f"TRN-{random.randint(1000, 9999)}" if is_occupied else None,
                    "block_reason": random.choice(["TRAIN", "MAINTENANCE", None]) if is_occupied else None,
                    "estimated_clear_time": self._calculate_clear_time() if is_occupied else None
                }
        
        return tracks

    def _get_weather_conditions(self) -> Dict:
        """Get weather conditions affecting operations"""
        conditions = ["CLEAR", "FOGGY", "RAINY", "STORMY"]
        visibility = ["GOOD", "POOR", "VERY_POOR"]
        
        current_weather = random.choice(conditions)
        impact = "LOW"
        if current_weather in ["FOGGY", "RAINY", "STORMY"]:
            impact = random.choice(["MEDIUM", "HIGH"])
        
        return {
            "condition": current_weather,
            "visibility": random.choice(visibility),
            "temperature": random.randint(15, 35),
            "impact_level": impact,
            "speed_restriction": random.randint(80, 130) if impact != "LOW" else None,
            "advisory": self._get_weather_advisory(current_weather)
        }

    def _get_system_alerts(self) -> List[Dict]:
        """Get system-wide alerts and notifications"""
        alerts = []
        alert_types = ["TRACK_MAINTENANCE", "SIGNAL_FAILURE", "POWER_ISSUE", "CONGESTION"]
        
        for _ in range(random.randint(0, 3)):
            alert_type = random.choice(alert_types)
            severity = random.choice(["LOW", "MEDIUM", "HIGH"])
            
            alerts.append({
                "type": alert_type,
                "severity": severity,
                "location": random.choice(list(self.delhi_stations.keys())),
                "description": self._get_alert_description(alert_type),
                "estimated_duration": random.randint(10, 180),  # minutes
                "affected_trains": random.randint(0, 5),
                "issued_at": datetime.now().strftime("%H:%M:%S")
            })
        
        return alerts

    def create_enhanced_scenario(self) -> Tuple[Section, List[Train]]:
        """
        Create an enhanced scenario based on real Delhi station data
        """
        # Create blocks based on Delhi stations
        blocks = []
        station_codes = list(self.delhi_stations.keys())[:7]  # Use 7 stations
        
        for i, station_code in enumerate(station_codes):
            station_info = self.delhi_stations[station_code]
            
            # Distance between stations (realistic Delhi distances)
            distances = [8, 12, 15, 10, 18, 14]
            distance = distances[i] if i < len(distances) else 10
            
            # Speed limits based on station type
            speed_limit = 110 if station_info["type"] == "major" else 90
            
            block = Block(
                id=station_code,
                length_km=distance,
                max_speed_kmph=speed_limit,
                direction="bi",
                station=station_info["name"],
                loop_capacity=min(station_info["platforms"] // 4, 3)
            )
            blocks.append(block)
        
        section = Section("DELHI-MAIN-SECTION", blocks, headway_min=3.0)
        
        # Create trains based on real-time data
        live_trains = self._get_live_trains()
        trains = []
        
        for i, live_train in enumerate(live_trains):
            train_type_info = self.train_types[live_train["type"]]
            
            # Create route using only available station blocks
            route = [code for code in live_train["route"] if code in station_codes]
            if len(route) < 3:  # Ensure minimum route length
                route = station_codes[:min(4, len(station_codes))]
            
            # Ensure route uses only available blocks
            route = route[:len(station_codes)]
            
            train = Train(
                id=live_train["train_number"],
                priority=train_type_info["priority"],
                max_speed_kmph=train_type_info["max_speed"],
                dwell_min=train_type_info["dwell_time"],
                route=route,
                direction=live_train["direction"].lower(),
                dep_time_min=i * 15,  # Stagger departures
                train_type=live_train["type"]
            )
            trains.append(train)
        
        return section, trains

    def _get_next_station(self, route: List[str], current: str) -> str:
        try:
            current_index = route.index(current)
            if current_index < len(route) - 1:
                return route[current_index + 1]
            else:
                return "DESTINATION"
        except ValueError:
            return "UNKNOWN"

    def _calculate_eta(self, delay: int) -> str:
        eta = datetime.now() + timedelta(minutes=random.randint(10, 60) + delay)
        return eta.strftime("%H:%M")

    def _calculate_clear_time(self) -> str:
        clear_time = datetime.now() + timedelta(minutes=random.randint(5, 30))
        return clear_time.strftime("%H:%M")

    def _get_weather_advisory(self, condition: str) -> str:
        advisories = {
            "CLEAR": "Normal operations",
            "FOGGY": "Reduced visibility - Speed restrictions in effect",
            "RAINY": "Wet weather operations - Exercise caution",
            "STORMY": "Severe weather - Possible service disruptions"
        }
        return advisories.get(condition, "Monitor conditions")

    def _get_alert_description(self, alert_type: str) -> str:
        descriptions = {
            "TRACK_MAINTENANCE": "Scheduled maintenance work in progress",
            "SIGNAL_FAILURE": "Signaling equipment malfunction detected",
            "POWER_ISSUE": "Power supply interruption reported",
            "CONGESTION": "High traffic volume causing delays"
        }
        return descriptions.get(alert_type, "System alert")

    def get_route_recommendations(self, occupied_blocks: List[str], 
                                destination: str, available_blocks: List[str] = None) -> List[Dict]:
        """
        Generate intelligent route recommendations when blocks are occupied
        """
        recommendations = []
        
        # Use available blocks if provided, otherwise use all Delhi stations
        if available_blocks:
            available_stations = available_blocks
        else:
            available_stations = list(self.delhi_stations.keys())[:7]  # Match enhanced scenario
        
        # Create simple alternative routes using available blocks
        simple_routes = [
            available_stations[:4],  # Route 1: First 4 stations
            available_stations[1:5] if len(available_stations) > 4 else available_stations[:3],  # Route 2: Middle stations
            available_stations[2:6] if len(available_stations) > 5 else available_stations[:4]   # Route 3: Later stations
        ]
        
        # Find alternative routes
        for route in simple_routes:
            # Check if route has occupied blocks
            occupied_count = sum(1 for block in route if block in occupied_blocks)
            
            # Calculate estimated time
            base_time = len(route) * 15  # 15 min per block base time
            delay_time = occupied_count * 20  # 20 min penalty per occupied block
            total_time = base_time + delay_time
            
            # Determine route efficiency
            efficiency = "HIGH" if occupied_count == 0 else "MEDIUM" if occupied_count < 2 else "LOW"
            
            recommendation = {
                "route": route,
                "occupied_blocks": [block for block in route if block in occupied_blocks],
                "estimated_time_minutes": total_time,
                "efficiency": efficiency,
                "recommendation": self._get_route_advice(occupied_count, total_time),
                "alternative_reason": self._get_alternative_reason(occupied_blocks, route)
            }
            
            recommendations.append(recommendation)
        
        # Sort by efficiency and time
        recommendations.sort(key=lambda x: (x["efficiency"] == "LOW", x["estimated_time_minutes"]))
        
        return recommendations[:3]  # Return top 3 recommendations

    def _get_route_advice(self, occupied_count: int, total_time: int) -> str:
        if occupied_count == 0:
            return "RECOMMENDED - Clear route, optimal travel time"
        elif occupied_count < 2 and total_time < 60:
            return "ACCEPTABLE - Minor delays expected"
        else:
            return "AVOID - Significant delays likely"

    def _get_alternative_reason(self, occupied_blocks: List[str], route: List[str]) -> str:
        route_occupied = [block for block in route if block in occupied_blocks]
        if not route_occupied:
            return "Clear route available"
        else:
            return f"Blocks {', '.join(route_occupied)} are occupied"
