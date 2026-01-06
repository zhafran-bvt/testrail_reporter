#!/usr/bin/env python3
"""
Test script to verify dataset generation integration.
"""

import time

import requests


def test_dataset_api():
    """Test the dataset generation API endpoints."""
    base_url = "http://localhost:8000"

    print("Testing Dataset Generation API Integration")
    print("=" * 50)

    # Test health endpoint
    print("1. Testing dataset health endpoint...")
    try:
        response = requests.get(f"{base_url}/api/dataset/health")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
    except Exception as e:
        print(f"   Error: {e}")

    # Test configuration endpoints
    print("\n2. Testing configuration endpoints...")
    try:
        areas_response = requests.get(f"{base_url}/api/dataset/config/areas")
        geometry_response = requests.get(f"{base_url}/api/dataset/config/geometry-types")
        labels_response = requests.get(f"{base_url}/api/dataset/config/labels")

        print(f"   Areas: {areas_response.status_code}")
        print(f"   Geometry Types: {geometry_response.status_code}")
        print(f"   Labels: {labels_response.status_code}")

        if areas_response.status_code == 200:
            areas = areas_response.json()
            print(f"   Available areas: {list(areas.get('areas', []))}")

    except Exception as e:
        print(f"   Error: {e}")

    # Test dataset generation (small dataset)
    print("\n3. Testing dataset generation...")
    try:
        config = {
            "rows": 10,
            "columns": 5,
            "geometry_type": "POINT",
            "format_type": "WKT",
            "area": "Jakarta",
            "include_demographic": True,
            "include_economic": False,
            "use_spatial_clustering": False,
            "filename_prefix": "test_integration",
        }

        response = requests.post(
            f"{base_url}/api/dataset/generate", json=config, headers={"Content-Type": "application/json"}
        )

        print(f"   Generation request status: {response.status_code}")

        if response.status_code == 200:
            job = response.json()
            job_id = job["job_id"]
            print(f"   Job ID: {job_id}")
            print(f"   Initial status: {job['status']}")

            # Poll job status
            print("\n4. Polling job status...")
            for i in range(30):  # Wait up to 30 seconds
                time.sleep(1)
                status_response = requests.get(f"{base_url}/api/dataset/jobs/{job_id}")

                if status_response.status_code == 200:
                    job_status = status_response.json()
                    print(f"   Attempt {i+1}: {job_status['status']}")

                    if job_status["status"] in ["completed", "failed"]:
                        print(f"   Final status: {job_status['status']}")
                        if job_status["status"] == "completed":
                            print(f"   Generated files: {job_status.get('file_paths', [])}")
                        elif job_status["status"] == "failed":
                            print(f"   Error: {job_status.get('error_message', 'Unknown error')}")
                        break
                else:
                    print(f"   Error checking status: {status_response.status_code}")
                    break

        else:
            print(f"   Error response: {response.text}")

    except Exception as e:
        print(f"   Error: {e}")

    # Test jobs listing
    print("\n5. Testing jobs listing...")
    try:
        response = requests.get(f"{base_url}/api/dataset/jobs")
        print(f"   Status: {response.status_code}")

        if response.status_code == 200:
            jobs = response.json()
            print(f"   Total jobs: {len(jobs)}")
            for job in jobs[:3]:  # Show first 3 jobs
                print(f"   - Job {job['job_id'][:8]}...: {job['status']}")

    except Exception as e:
        print(f"   Error: {e}")

    print("\n" + "=" * 50)
    print("Integration test completed!")
    print("\nTo test the UI:")
    print("1. Start the server: uvicorn app.main:app --reload")
    print("2. Open http://localhost:8000")
    print("3. Click on 'Dataset Generator' in the navigation")
    print("4. Fill out the form and click 'Generate Dataset'")


if __name__ == "__main__":
    test_dataset_api()
