from enum import Enum


class Tools(str, Enum):
    # SlideSpeak tools
    GET_AVAILABLE_TEMPLATES = "get_available_templates"
    GENERATE_POWERPOINT = "generate_powerpoint"
    GENERATE_POWERPOINT_SLIDE_BY_SLIDE = "generate_powerpoint_slide_by_slide"
