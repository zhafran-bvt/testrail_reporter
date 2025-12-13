"""Dataset generation API endpoints."""

# Import dataset generator functions
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from pydantic import BaseModel

# Import models
from app.models.requests import DatasetConfig

sys.path.append(str(Path(__file__).parent.parent.parent.parent / "dataset_generator"))

try:
    import geopandas as gpd
    from shapely.ops import unary_union

    from dataset_generator.file_generator import (  # type: ignore
        BOUNDING_BOXES,
        H3_AVAILABLE,
        REALISTIC_LABELS,
        generate_parallel_dataframe,
        save_files_chunked,
        validate_generated_data,
    )

    DATASET_GENERATOR_AVAILABLE = True
except ImportError as e:
    print(f"Dataset generator not available: {e}")
    DATASET_GENERATOR_AVAILABLE = False

router = APIRouter(prefix="/api/dataset", tags=["dataset"])


class DatasetGenerationJob(BaseModel):
    """Dataset generation job status."""

    job_id: str
    status: str  # "pending", "running", "completed", "failed"
    config: DatasetConfig
    created_at: str
    completed_at: Optional[str] = None
    file_paths: List[str] = []
    error_message: Optional[str] = None
    validation_results: Optional[Dict[str, Any]] = None


# In-memory job storage (in production, use Redis or database)
_jobs: Dict[str, DatasetGenerationJob] = {}


def _get_area_config(area_name: str) -> Dict[str, Any]:
    """Get bounding box configuration for area."""
    area_map = {"Jakarta": 1, "Yogyakarta": 2, "Indonesia": 3, "Japan": 4, "Vietnam": 5}

    area_id = area_map.get(area_name)
    if not area_id:
        raise ValueError(f"Unknown area: {area_name}")

    return BOUNDING_BOXES[area_id]


def _get_geometry_type_id(geom_type: str) -> int:
    """Convert geometry type string to ID."""
    type_map = {"POINT": 1, "POLYGON": 2, "MULTIPOLYGON": 3, "H3": 4}

    geom_id = type_map.get(geom_type.upper())
    if not geom_id:
        raise ValueError(f"Unknown geometry type: {geom_type}")

    if geom_id == 4 and not H3_AVAILABLE:
        raise ValueError("H3 geometry type requires h3 library installation")

    return geom_id


async def _generate_dataset_task(job_id: str, config: DatasetConfig):
    """Background task to generate dataset."""
    job = _jobs[job_id]
    job.status = "running"

    try:
        # Get area configuration
        area_config = _get_area_config(config.area)
        lon_min, lon_max = area_config["lon_min"], area_config["lon_max"]
        lat_min, lat_max = area_config["lat_min"], area_config["lat_max"]

        # Load land geometry if geojson_path provided
        land_geometry = None
        if config.geojson_path and Path(config.geojson_path).exists():
            try:
                land_gdf = gpd.read_file(config.geojson_path)
                if not land_gdf.empty:
                    land_geometry = unary_union(land_gdf["geometry"].values)
            except Exception as e:
                print(f"Warning: Could not load GeoJSON file: {e}")

        # Generate dataset
        df = generate_parallel_dataframe(
            rows=config.rows,
            cols=config.columns,
            geom_type=config.geometry_type,
            format_type=config.format_type,
            lon_min=lon_min,
            lon_max=lon_max,
            lat_min=lat_min,
            lat_max=lat_max,
            land_geometry=land_geometry,
            include_demographic=config.include_demographic,
            include_economic=config.include_economic,
            use_spatial_clustering=config.use_spatial_clustering,
            h3_resolution=9 if config.geometry_type == "H3" else None,
        )

        # Validate dataset
        df, validation_results = validate_generated_data(
            df=df,
            geom_type=config.geometry_type,
            format_type=config.format_type,
            lon_min=lon_min,
            lon_max=lon_max,
            lat_min=lat_min,
            lat_max=lat_max,
            h3_resolution=9 if config.geometry_type == "H3" else None,
            land_geometry=land_geometry,
        )

        # Generate filename
        area_name = config.area.lower()
        geom_suffix = (
            "h3_res9"
            if config.geometry_type == "H3"
            else f"{config.geometry_type.lower()}_{config.format_type.lower()}"
        )
        filename_prefix = (
            config.filename_prefix or f"{area_name}_testdata_{config.rows}r_{config.columns}c_{geom_suffix}"
        )

        # Save files
        save_files_chunked(df, filename_prefix)

        # Update job status
        job.status = "completed"
        job.validation_results = validation_results
        job.file_paths = [f"output/{filename_prefix}.csv", f"output/{filename_prefix}.xlsx"]
        job.completed_at = datetime.now().isoformat()

    except Exception as e:
        job.status = "failed"
        job.error_message = str(e)
        job.completed_at = datetime.now().isoformat()


@router.post("/generate", response_model=DatasetGenerationJob)
async def generate_dataset(config: DatasetConfig, background_tasks: BackgroundTasks):
    """Generate a synthetic dataset for testing purposes."""
    if not DATASET_GENERATOR_AVAILABLE:
        raise HTTPException(
            status_code=503, detail="Dataset generator is not available. Please install required dependencies."
        )

    # Validate configuration
    try:
        _get_area_config(config.area)
        _get_geometry_type_id(config.geometry_type)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Create job
    import uuid
    from datetime import datetime

    job_id = str(uuid.uuid4())
    job = DatasetGenerationJob(job_id=job_id, status="pending", config=config, created_at=datetime.now().isoformat())

    _jobs[job_id] = job

    # Start background task
    background_tasks.add_task(_generate_dataset_task, job_id, config)

    return job


@router.get("/jobs/{job_id}", response_model=DatasetGenerationJob)
async def get_job_status(job_id: str):
    """Get status of a dataset generation job."""
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    return _jobs[job_id]


@router.get("/jobs", response_model=List[DatasetGenerationJob])
async def list_jobs(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of jobs to return"),
):
    """List dataset generation jobs."""
    jobs = list(_jobs.values())

    if status:
        jobs = [job for job in jobs if job.status == status]

    # Sort by created_at descending
    jobs.sort(key=lambda x: x.created_at, reverse=True)

    return jobs[:limit]


@router.get("/config/areas")
async def get_available_areas():
    """Get list of available geographic areas."""
    return {
        "areas": list(BOUNDING_BOXES.keys()),
        "area_details": {
            name: {
                "name": config["name"],
                "bounds": {
                    "lon_min": config["lon_min"],
                    "lon_max": config["lon_max"],
                    "lat_min": config["lat_min"],
                    "lat_max": config["lat_max"],
                },
            }
            for name, config in BOUNDING_BOXES.items()
        },
    }


@router.get("/config/geometry-types")
async def get_geometry_types():
    """Get list of available geometry types."""
    types = ["POINT", "POLYGON", "MULTIPOLYGON"]
    if H3_AVAILABLE:
        types.append("H3")

    return {"geometry_types": types, "h3_available": H3_AVAILABLE}


@router.get("/config/labels")
async def get_available_labels():
    """Get list of available data labels."""
    return {
        "realistic_labels": REALISTIC_LABELS,
        "demographic_labels": ["Gender", "Occupation", "Education Level"],
        "economic_labels": ["Household Income", "Employment Status", "Access to Healthcare"],
    }


@router.delete("/jobs/{job_id}")
async def delete_job(job_id: str):
    """Delete a dataset generation job."""
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = _jobs[job_id]

    # Clean up generated files
    for file_path in job.file_paths:
        try:
            Path(file_path).unlink(missing_ok=True)
        except Exception:
            pass

    del _jobs[job_id]

    return {"message": f"Job {job_id} deleted successfully"}


@router.get("/health")
async def dataset_health():
    """Health check for dataset generation service."""
    return {
        "status": "healthy" if DATASET_GENERATOR_AVAILABLE else "unavailable",
        "dataset_generator_available": DATASET_GENERATOR_AVAILABLE,
        "h3_available": H3_AVAILABLE if DATASET_GENERATOR_AVAILABLE else False,
        "active_jobs": len([job for job in _jobs.values() if job.status in ["pending", "running"]]),
        "total_jobs": len(_jobs),
    }
