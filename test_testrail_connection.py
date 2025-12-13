#!/usr/bin/env python3
"""
TestRail Connection Test Script
Run this to verify your TestRail API credentials are working.
"""

import os

import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def test_testrail_connection():
    """Test TestRail API connection and list projects."""

    # Get credentials from environment
    base_url = os.getenv("TESTRAIL_BASE_URL")
    user = os.getenv("TESTRAIL_USER")
    api_key = os.getenv("TESTRAIL_API_KEY")

    print("🔍 Testing TestRail Connection...")
    print(f"📍 URL: {base_url}")
    print(f"👤 User: {user}")
    print(f"🔑 API Key: {'*' * (len(api_key) - 4) + api_key[-4:] if api_key else 'Not set'}")
    print("-" * 50)

    if not all([base_url, user, api_key]):
        print("❌ Missing credentials! Please update .env file with your TestRail credentials.")
        return False

    # Test API connection
    try:
        url = f"{base_url}/index.php?/api/v2/get_projects"
        response = requests.get(url, auth=(user, api_key), timeout=10)

        if response.status_code == 200:
            projects = response.json()
            print("✅ Connection successful!")
            print(f"📊 Found {len(projects)} projects:")

            for i, project in enumerate(projects[:5], 1):  # Show first 5 projects
                print(f"   {i}. ID: {project['id']} - {project['name']}")

            if len(projects) > 5:
                print(f"   ... and {len(projects) - 5} more projects")

            return True

        elif response.status_code == 401:
            print("❌ Authentication failed! Check your email and API key.")
            return False

        elif response.status_code == 403:
            print("❌ Access denied! Your API key may not have sufficient permissions.")
            return False

        else:
            print(f"❌ API Error: {response.status_code} - {response.text}")
            return False

    except requests.exceptions.ConnectionError:
        print("❌ Connection failed! Check your TESTRAIL_BASE_URL.")
        return False

    except requests.exceptions.Timeout:
        print("❌ Connection timeout! TestRail server may be slow or unreachable.")
        return False

    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


def test_specific_project(project_id=1):
    """Test getting plans for a specific project."""

    base_url = os.getenv("TESTRAIL_BASE_URL")
    user = os.getenv("TESTRAIL_USER")
    api_key = os.getenv("TESTRAIL_API_KEY")

    print(f"\n🔍 Testing Project {project_id} Plans...")

    try:
        url = f"{base_url}/index.php?/api/v2/get_plans/{project_id}"
        response = requests.get(url, auth=(user, api_key), timeout=10)

        if response.status_code == 200:
            plans = response.json()
            print(f"✅ Found {len(plans)} plans in project {project_id}")

            for i, plan in enumerate(plans[:3], 1):  # Show first 3 plans
                print(f"   {i}. ID: {plan['id']} - {plan['name']}")

            return True
        else:
            print(f"❌ Failed to get plans: {response.status_code} - {response.text}")
            return False

    except Exception as e:
        print(f"❌ Error getting plans: {e}")
        return False


if __name__ == "__main__":
    print("🚀 TestRail Connection Test")
    print("=" * 50)

    # Test basic connection
    if test_testrail_connection():
        # Test specific project
        test_specific_project(1)

        print("\n✅ TestRail connection is working!")
        print("💡 You can now restart the server and it should show data.")
    else:
        print("\n❌ Please fix the credentials and try again.")
        print("\n📝 Steps to fix:")
        print("1. Update .env file with your real TestRail credentials")
        print("2. Get API key from TestRail → My Settings → API Keys")
        print("3. Run this script again to test")
