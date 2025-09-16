"""
Role Play Templates and Configuration
"""
from typing import Dict, Any

# Role Play Templates
ROLE_PLAY_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "school": {
        "name": "School",
        "description": "Educational institution role play",
        "defaultRole": "Teacher",
        "icon": "🏫",
        "placeholder": "e.g., ABC International School, 500 students, modern facilities...",
        "scenarios": [
            "Parent-teacher conference",
            "Student enrollment",
            "Academic counseling",
            "School event planning"
        ]
    },
    "company": {
        "name": "Software Company",
        "description": "Business/tech company role play",
        "defaultRole": "Software Developer",
        "icon": "🏢",
        "placeholder": "e.g., TechCorp Solutions, 50 employees, web development...",
        "scenarios": [
            "Job interview",
            "Team meeting",
            "Project discussion",
            "Client presentation"
        ]
    },
    "restaurant": {
        "name": "Restaurant",
        "description": "Food service role play",
        "defaultRole": "Waiter",
        "icon": "🍽️",
        "placeholder": "e.g., Bella Vista Restaurant, Italian cuisine, family-owned...",
        "scenarios": [
            "Taking orders",
            "Handling complaints",
            "Menu recommendations",
            "Reservation management"
        ]
    },
    "hospital": {
        "name": "Hospital",
        "description": "Healthcare role play",
        "defaultRole": "Nurse",
        "icon": "🏥",
        "placeholder": "e.g., City General Hospital, 200 beds, emergency services...",
        "scenarios": [
            "Patient admission",
            "Medical consultation",
            "Emergency response",
            "Family communication"
        ]
    },
    "custom": {
        "name": "Custom",
        "description": "Custom role play scenario",
        "defaultRole": "Professional",
        "icon": "⚙️",
        "placeholder": "Describe your custom scenario...",
        "scenarios": [
            "Custom scenario 1",
            "Custom scenario 2",
            "Custom scenario 3"
        ]
    }
}

# Role Play Difficulty Levels
DIFFICULTY_LEVELS = {
    "easy": {
        "name": "Easy",
        "description": "Simple vocabulary, slow pace",
        "complexity": 0.7,
        "speed": 0.8
    },
    "medium": {
        "name": "Medium", 
        "description": "Standard vocabulary, normal pace",
        "complexity": 1.0,
        "speed": 1.0
    },
    "fast": {
        "name": "Fast",
        "description": "Advanced vocabulary, quick pace",
        "complexity": 1.3,
        "speed": 1.2
    }
}

