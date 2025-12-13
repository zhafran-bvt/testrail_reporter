#!/usr/bin/env python3
"""
Setup script for dataset generator integration.
"""

import subprocess
import sys
from pathlib import Path


def setup_integration():
    """Set up the dataset generator integration."""
    print("Setting up Dataset Generator Integration")
    print("=" * 50)

    # Check if we're in the right directory
    current_dir = Path.cwd()
    if not (current_dir / "app" / "main.py").exists():
        print("Error: Please run this script from the testrail_daily_report directory")
        sys.exit(1)

    # Check if dataset_generator directory exists
    dataset_dir = current_dir.parent / "dataset_generator"
    if not dataset_dir.exists():
        print(f"Error: Dataset generator directory not found at {dataset_dir}")
        print("Please ensure both projects are in the same parent directory:")
        print("  parent_directory/")
        print("    ├── dataset_generator/")
        print("    └── testrail_daily_report/")
        sys.exit(1)

    print(f"✓ Found dataset generator at: {dataset_dir}")

    # Check if required files exist in dataset generator
    required_files = ["file_generator.py", "h3_config.json", "point_config.json"]

    for file in required_files:
        if not (dataset_dir / file).exists():
            print(f"Warning: {file} not found in dataset generator directory")

    # Install additional requirements
    print("\n1. Installing additional Python packages...")
    try:
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "geopandas==0.14.4",
                "shapely==2.0.4",
                "h3==3.7.7",
                "numpy==1.26.4",
                "scipy==1.13.1",
                "tqdm==4.66.4",
            ],
            check=True,
        )
        print("✓ Additional packages installed successfully")
    except subprocess.CalledProcessError as e:
        print(f"Error installing packages: {e}")
        print("You may need to install them manually:")
        print("pip install geopandas shapely h3 numpy scipy tqdm")

    # Create output directory
    output_dir = current_dir / "out"
    output_dir.mkdir(exist_ok=True)
    print(f"✓ Created output directory: {output_dir}")

    # Check if the integration is working
    print("\n2. Testing integration...")
    try:
        # Try importing the dataset API
        sys.path.append(str(current_dir))
        import importlib.util

        spec = importlib.util.find_spec("app.api.dataset")
        if spec is not None:
            print("✓ Dataset API module found successfully")
        else:
            print("Warning: Dataset API module not found")
    except ImportError as e:
        print(f"Warning: Could not import dataset API: {e}")
        print("This might be due to missing dependencies")

    print("\n3. Setup completed!")
    print("\nNext steps:")
    print("1. Start the server:")
    print("   uvicorn app.main:app --reload")
    print("\n2. Open your browser to:")
    print("   http://localhost:8000")
    print("\n3. Click on 'Dataset Generator' in the navigation")
    print("\n4. Test the integration:")
    print("   python test_dataset_integration.py")

    print("\nTroubleshooting:")
    print("- If you get import errors, make sure all dependencies are installed")
    print("- If dataset generation fails, check that the dataset_generator directory is accessible")
    print("- Check the server logs for detailed error messages")


if __name__ == "__main__":
    setup_integration()
