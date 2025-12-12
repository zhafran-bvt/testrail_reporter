# Design Document

## Overview

This design document outlines the architectural improvements for the TestRail Reporter application, focusing on five key areas: modularization, error handling, performance optimization, frontend modernization, and documentation enhancement. The design maintains backward compatibility while significantly improving code maintainability and user experience.

## Architecture

### Current Architecture
```
app/
├── main.py (3,134 lines - monolithic)
├── dashboard_stats.py
└── __init__.py

src/ (Frontend)
├── app.ts (vanilla TypeScript)
├── utils.ts
├── views.ts
└── ... (multiple utility files)
```

### Target Architecture
```
app/
├── main.py (entry point only)
├── api/
│   ├── __init__.py
│   ├── dashboard.py
│   ├── management.py
│   ├── reports.py
│   └── health.py
├── models/
│   ├── __init__.py
│   ├── requests.py
│   └── responses.py
├── services/
│   ├── __init__.py
│   ├── cache.py
│   ├── testrail_client.py
│   ├── error_handler.py
│   └── performance.py
├── core/
│   ├── __init__.py
│   ├── dependencies.py
│   ├── config.py
│   └── middleware.py
└── utils/
    ├── __init__.py
    └── helpers.py

frontend/ (React)
├── src/
│   ├── components/
│   ├── hooks/
│   ├── services/
│   ├── types/
│   └── App.tsx
├── package.json
└── tsconfig.json
```

## Components and Interfaces

### 1. API Router Modules

**Dashboard Router (`app/api/dashboard.py`)**
- Handles all dashboard-related endpoints
- Manages plan statistics and caching
- Provides paginated responses

**Management Router (`app/api/management.py`)**
- Handles CRUD operations for plans, runs, cases
- Implements dry-run functionality
- Manages file uploads and attachments

**Reports Router (`app/api/reports.py`)**
- Handles report generation endpoints
- Manages async job processing
- Provides report status tracking

### 2. Service Layer

**Cache Service (`app/services/cache.py`)**
```python
class CacheService:
    def get(self, key: str) -> Any | None
    def set(self, key: str, value: Any, ttl: int = None) -> None
    def delete(self, key: str) -> bool
    def clear_pattern(self, pattern: str) -> int
```

**TestRail Client Service (`app/services/testrail_client.py`)**
```python
class TestRailClientService:
    def get_client(self) -> TestRailClient
    def batch_requests(self, requests: list) -> list
    def with_retry(self, func: callable, *args, **kwargs) -> Any
```

**Error Handler Service (`app/services/error_handler.py`)**
```python
class ErrorHandler:
    def handle_exception(self, exc: Exception, request: Request) -> JSONResponse
    def log_error(self, exc: Exception, context: dict) -> str  # returns correlation_id
    def format_validation_error(self, exc: ValidationError) -> dict
```

### 3. Frontend Components (React)

**Component Structure**
```typescript
// Core Components
- App.tsx (main application)
- Layout.tsx (navigation and layout)
- ErrorBoundary.tsx (error handling)

// Feature Components
- Dashboard/
  - PlansList.tsx
  - PlanCard.tsx
  - StatisticsChart.tsx
- Management/
  - CreatePlan.tsx
  - EditPlan.tsx
  - DeleteConfirmation.tsx
- Reports/
  - ReportGenerator.tsx
  - ProgressIndicator.tsx
```

## Data Models

### Request Models
```python
# Consolidated from existing Pydantic models
class PlanRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    milestone_id: Optional[int] = None

class RunRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    plan_id: Optional[int] = None
    case_ids: Optional[list[int]] = None
```

### Response Models
```python
class ErrorResponse(BaseModel):
    detail: str
    error_code: str
    timestamp: str
    correlation_id: str

class SuccessResponse(BaseModel):
    success: bool = True
    data: Optional[dict] = None
    meta: Optional[dict] = None
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Module Loading Consistency
*For any* application startup, all API router modules should load successfully and register their endpoints without conflicts
**Validates: Requirements 1.1, 1.3**

### Property 2: Dependency Injection Usage
*For any* API endpoint, dependencies should be injected via FastAPI's dependency system rather than using global variables
**Validates: Requirements 1.4**

### Property 3: Backward Compatibility Preservation
*For any* existing API endpoint, the refactored system should maintain the same request/response contract and behavior
**Validates: Requirements 1.5, 4.5**

### Property 4: Error Response Consistency
*For any* error condition, the system should return a structured error response with consistent JSON format including error codes and timestamps
**Validates: Requirements 2.1**

### Property 5: Retry Logic Implementation
*For any* transient TestRail API failure, the system should implement exponential backoff retry logic with appropriate limits
**Validates: Requirements 2.2**

### Property 6: Exception Handling Completeness
*For any* unhandled exception, the system should log full context and return a safe error message with correlation ID
**Validates: Requirements 2.3, 2.5**

### Property 7: Validation Error Detail
*For any* validation error, the system should provide field-level error messages that help users correct their input
**Validates: Requirements 2.4**

### Property 8: Cache Efficiency
*For any* cacheable request, the system should use improved cache key strategies and respect TTL settings
**Validates: Requirements 3.1**

### Property 9: Connection Optimization
*For any* large TestRail plan processing, the system should use connection pooling and request batching to minimize API calls
**Validates: Requirements 3.2**

### Property 10: Memory Efficiency
*For any* large dataset report generation, the system should use streaming responses to maintain stable memory usage
**Validates: Requirements 3.3**

### Property 11: Concurrency Handling
*For any* concurrent request load, the system should handle requests efficiently without blocking or resource exhaustion
**Validates: Requirements 3.5**

### Property 12: React Integration
*For any* UI component, the system should use React with TypeScript and provide reactive state updates
**Validates: Requirements 4.1, 4.3**

### Property 13: Form Validation Reactivity
*For any* form interaction, the system should provide real-time validation feedback without page reloads
**Validates: Requirements 4.2**

## Error Handling

### Error Classification
1. **Validation Errors** (400) - Client input validation failures
2. **Authentication Errors** (401) - Missing or invalid credentials
3. **Authorization Errors** (403) - Insufficient permissions
4. **Not Found Errors** (404) - Resource not found
5. **TestRail API Errors** (502) - External API failures
6. **Server Errors** (500) - Internal application errors

### Error Response Format
```json
{
  "detail": "Human-readable error message",
  "error_code": "VALIDATION_ERROR",
  "timestamp": "2024-12-12T10:30:00Z",
  "correlation_id": "req_abc123def456",
  "field_errors": {
    "name": ["Field is required"],
    "email": ["Invalid email format"]
  }
}
```

### Retry Strategy
- **Transient Errors**: 429, 5xx status codes, timeouts, connection errors
- **Retry Limits**: Maximum 3 attempts with exponential backoff
- **Backoff Formula**: `delay = base_delay * (2 ^ attempt) + jitter`
- **Circuit Breaker**: Open circuit after 5 consecutive failures

## Testing Strategy

### Unit Testing
- **Model Validation**: Test all Pydantic models with valid/invalid inputs
- **Service Logic**: Test cache operations, error handling, and business logic
- **Utility Functions**: Test helper functions and data transformations

### Integration Testing
- **API Endpoints**: Test all endpoints with mocked TestRail client
- **Error Scenarios**: Test error handling paths and response formats
- **Cache Behavior**: Test cache hits, misses, and TTL expiration

### Property-Based Testing
- **Error Response Format**: Generate random error conditions and verify consistent response structure
- **Cache Key Generation**: Test cache key uniqueness and collision resistance
- **Retry Logic**: Test retry behavior with various failure patterns
- **Validation Rules**: Test input validation with generated test data

### Frontend Testing
- **Component Tests**: Test React components with React Testing Library
- **Integration Tests**: Test user workflows with Cypress or Playwright
- **State Management**: Test React hooks and context providers

### Performance Testing
- **Load Testing**: Test concurrent request handling with locust or similar
- **Memory Testing**: Monitor memory usage during large report generation
- **Cache Performance**: Measure cache hit rates and response times

The testing approach combines traditional unit/integration tests with property-based testing to ensure both specific functionality and general correctness properties are validated.