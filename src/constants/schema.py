from pydantic import BaseModel
from typing import Optional, List, Dict, Any

# SlideSpeak schemas
class GetAvailableTemplates(BaseModel):
    limit: Optional[int] = None  # Optional limit on number of templates to return

class GeneratePowerpoint(BaseModel):
    plain_text: str
    length: int
    template: str

class GeneratePowerpointSlideBySlide(BaseModel):
    slides: List[Dict[str, Any]]
    template: str
