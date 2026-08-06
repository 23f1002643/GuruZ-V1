"""Integration tests for the FastAPI endpoints."""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


@pytest.mark.asyncio
async def test_health_check(client):
    response = await client.get("/api/healthz")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_detailed_health(client):
    response = await client.get("/api/health/detailed")
    assert response.status_code == 200
    data = response.json()
    assert "llm_provider" in data
    assert "chromadb_status" in data
    assert "uptime_seconds" in data


@pytest.mark.asyncio
async def test_list_jobs_empty(client):
    response = await client.get("/api/jobs")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_get_job_not_found(client):
    response = await client.get("/api/jobs/nonexistent-job-id")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_packages_empty(client):
    response = await client.get("/api/packages")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_get_package_not_found(client):
    response = await client.get("/api/packages/nonexistent-package-id")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_logs(client):
    response = await client.get("/api/logs")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_get_settings(client):
    response = await client.get("/api/settings")
    assert response.status_code == 200
    data = response.json()
    assert "llm_provider" in data
    assert "nvidia_model" in data


@pytest.mark.asyncio
async def test_package_stats(client):
    response = await client.get("/api/packages/stats/summary")
    assert response.status_code == 200
    data = response.json()
    assert "total_packages" in data
    assert "subjects" in data


@pytest.mark.asyncio
async def test_upload_invalid_file_type(client):
    import io
    response = await client.post(
        "/api/upload",
        files={"file": ("test.exe", io.BytesIO(b"fake content"), "application/octet-stream")},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_upload_no_file(client):
    response = await client.post("/api/upload")
    assert response.status_code == 422  # Missing required field
