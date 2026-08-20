from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.services.component_taxonomy import ComponentDefinition, get_all_components, get_component

router = APIRouter(prefix="/components", tags=["components"])


@router.get("", response_model=List[dict])
def list_components() -> List[dict]:
    components = get_all_components()
    return [
        {
            "component_id": c.component_id,
            "display_name": c.display_name,
            "system_category": c.system_category,
            "vehicle_region": c.vehicle_region,
            "description": c.description,
        }
        for c in components
    ]


@router.get("/{component_id}", response_model=dict)
def get_component_detail(component_id: str) -> dict:
    component = get_component(component_id)
    if component is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Component not found")
    return {
        "component_id": component.component_id,
        "display_name": component.display_name,
        "system_category": component.system_category,
        "vehicle_region": component.vehicle_region,
        "description": component.description,
    }
