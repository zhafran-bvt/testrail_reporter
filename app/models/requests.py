"""Request models for API endpoints."""

from pydantic import BaseModel, field_validator, model_validator


class ReportRequest(BaseModel):
    project: int = 1
    plan: int | None = None
    run: int | None = None
    run_ids: list[int] | None = None

    @field_validator("run_ids", mode="before")
    @classmethod
    def _coerce_run_ids(cls, value):
        if value is None:
            return None
        if isinstance(value, (str, int)):
            value = [value]
        if isinstance(value, tuple):
            value = list(value)
        cleaned: list[int] = []
        for item in value:
            if item is None:
                continue
            text = str(item).strip()
            if not text:
                continue
            cleaned.append(int(text))
        return cleaned or None

    @model_validator(mode="after")
    def _validate_constraints(self):
        if (self.plan is None and self.run is None) or (self.plan is not None and self.run is not None):
            raise ValueError("Provide exactly one of plan or run")
        if self.run_ids and self.plan is None:
            raise ValueError("Run selection requires a plan")
        return self


class ManagePlan(BaseModel):
    project: int = 1
    name: str
    description: str | None = None
    milestone_id: int | None = None
    dry_run: bool = False


class ManageRun(BaseModel):
    project: int = 1
    plan_id: int | None = None
    name: str
    description: str | None = None
    refs: str | None = None
    include_all: bool = True
    case_ids: list[int] | None = None
    dry_run: bool = False

    @model_validator(mode="after")
    def _validate_cases(self):
        if not self.include_all and not self.case_ids:
            raise ValueError("Provide case_ids when include_all is false")
        return self


class ManageCase(BaseModel):
    project: int = 1
    title: str
    refs: str | None = None
    bdd_scenarios: str | None = None
    dry_run: bool = False


class UpdatePlan(BaseModel):
    name: str | None = None
    description: str | None = None
    milestone_id: int | None = None
    dry_run: bool = False

    @model_validator(mode="after")
    def _validate_not_all_empty(self):
        if self.name is not None and not self.name.strip():
            raise ValueError("Plan name cannot be empty")
        return self


class UpdateRun(BaseModel):
    name: str | None = None
    description: str | None = None
    refs: str | None = None
    dry_run: bool = False

    @model_validator(mode="after")
    def _validate_not_all_empty(self):
        if self.name is not None and not self.name.strip():
            raise ValueError("Run name cannot be empty")
        return self


class UpdateCase(BaseModel):
    title: str | None = None
    refs: str | None = None
    bdd_scenarios: str | None = None
    dry_run: bool = False

    @model_validator(mode="after")
    def _validate_not_all_empty(self):
        if self.title is not None and not self.title.strip():
            raise ValueError("Case title cannot be empty")
        return self


class AddTestResult(BaseModel):
    """Model for adding a test result."""

    status_id: int
    comment: str | None = None
    elapsed: str | None = None
    defects: str | None = None
    version: str | None = None
    assignedto_id: int | None = None


class DatasetConfig(BaseModel):
    """Configuration for dataset generation."""

    rows: int = 1000
    columns: int = 10
    geometry_type: str = "POINT"
    format_type: str = "WKT"
    area: str = "Jakarta"
    include_demographic: bool = True
    include_economic: bool = True
    use_spatial_clustering: bool = False
    geojson_path: str | None = None
    filename_prefix: str | None = None

    @field_validator("rows")
    @classmethod
    def validate_rows(cls, v):
        if not (1 <= v <= 1000000):
            raise ValueError("Rows must be between 1 and 1,000,000")
        return v

    @field_validator("columns")
    @classmethod
    def validate_columns(cls, v):
        if not (3 <= v <= 29):
            raise ValueError("Columns must be between 3 and 29")
        return v

    @field_validator("geometry_type")
    @classmethod
    def validate_geometry_type(cls, v):
        valid_types = ["POINT", "POLYGON", "MULTIPOLYGON", "H3"]
        if v.upper() not in valid_types:
            raise ValueError(f"Geometry type must be one of: {valid_types}")
        return v.upper()

    @field_validator("format_type")
    @classmethod
    def validate_format_type(cls, v):
        valid_formats = ["WKT", "GEOJSON"]
        if v.upper() not in valid_formats:
            raise ValueError(f"Format type must be one of: {valid_formats}")
        return v.upper()

    @field_validator("area")
    @classmethod
    def validate_area(cls, v):
        valid_areas = ["Jakarta", "Yogyakarta", "Indonesia", "Japan", "Vietnam"]
        if v not in valid_areas:
            raise ValueError(f"Area must be one of: {valid_areas}")
        return v
