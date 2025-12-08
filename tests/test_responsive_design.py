"""
Tests for responsive design implementation in Management view.

Validates:
- Requirements 10.1, 10.2, 10.3, 10.4, 10.5
"""

import re
from pathlib import Path


def test_responsive_media_queries_exist():
    """Test that responsive media queries are present in the HTML."""
    html_path = Path("templates/index.html")
    html_content = html_path.read_text()

    # Check for desktop breakpoint (min-width: 1025px)
    assert re.search(
        r"@media\s*\(min-width:\s*1025px\)", html_content
    ), "Desktop media query (min-width: 1025px) not found"

    # Check for tablet breakpoint (768px - 1024px)
    assert re.search(
        r"@media\s*\(max-width:\s*1024px\)\s*and\s*\(min-width:\s*768px\)", html_content
    ), "Tablet media query (768px - 1024px) not found"

    # Check for mobile breakpoint (max-width: 767px)
    assert re.search(
        r"@media\s*\(max-width:\s*767px\)", html_content
    ), "Mobile media query (max-width: 767px) not found"

    # Check for extra small mobile breakpoint (max-width: 479px)
    assert re.search(
        r"@media\s*\(max-width:\s*479px\)", html_content
    ), "Extra small mobile media query (max-width: 479px) not found"


def test_create_forms_grid_responsive():
    """Test that create forms grid has responsive column definitions."""
    html_path = Path("templates/index.html")
    html_content = html_path.read_text()

    # Desktop: 3 columns
    assert re.search(
        r"\.create-forms-grid\s*\{[^}]*grid-template-columns:\s*repeat\(3,\s*1fr\)", html_content
    ), "Desktop create forms grid (3 columns) not found"

    # Tablet: 2 columns
    tablet_section = re.search(
        r"@media\s*\(max-width:\s*1024px\)\s*and\s*\(min-width:\s*768px\)\s*\{(.*?)\}", html_content, re.DOTALL
    )
    assert tablet_section, "Tablet media query section not found"
    assert re.search(
        r"\.create-forms-grid\s*\{[^}]*grid-template-columns:\s*repeat\(2,\s*1fr\)", tablet_section.group(1)
    ), "Tablet create forms grid (2 columns) not found"

    # Mobile: 1 column
    mobile_section = re.search(r"@media\s*\(max-width:\s*767px\)\s*\{(.*?)(?=@media|\Z)", html_content, re.DOTALL)
    assert mobile_section, "Mobile media query section not found"
    assert re.search(
        r"\.create-forms-grid\s*\{[^}]*grid-template-columns:\s*1fr", mobile_section.group(1)
    ), "Mobile create forms grid (1 column) not found"


def test_touch_friendly_buttons():
    """Test that buttons have touch-friendly sizing on mobile."""
    html_path = Path("templates/index.html")
    html_content = html_path.read_text()

    # Check for touch-friendly media query
    touch_query = re.search(
        r"@media\s*\(max-width:\s*767px\)\s*and\s*\(hover:\s*none\)\s*\{(.*?)\}", html_content, re.DOTALL
    )
    assert touch_query, "Touch-friendly media query not found"

    # Check for min-height: 44px (iOS recommended touch target size)
    assert re.search(r"min-height:\s*44px", touch_query.group(1)), "Touch-friendly min-height (44px) not found"


def test_manage_subsection_responsive():
    """Test that manage subsections have responsive styling."""
    html_path = Path("templates/index.html")
    html_content = html_path.read_text()

    # Check for mobile subsection styling
    mobile_section = re.search(r"@media\s*\(max-width:\s*767px\)\s*\{(.*?)(?=@media|\Z)", html_content, re.DOTALL)
    assert mobile_section, "Mobile media query section not found"

    # Check for subsection padding adjustments
    assert re.search(
        r"\.manage-subsection\s*\{[^}]*padding:\s*16px", mobile_section.group(1)
    ), "Mobile manage subsection padding not found"


def test_entity_card_actions_responsive():
    """Test that entity card actions stack vertically on mobile."""
    html_path = Path("templates/index.html")
    html_content = html_path.read_text()

    # Check for mobile entity card actions styling
    mobile_section = re.search(r"@media\s*\(max-width:\s*767px\)\s*\{(.*?)(?=@media|\Z)", html_content, re.DOTALL)
    assert mobile_section, "Mobile media query section not found"

    # Check for flex-direction: column
    assert re.search(
        r"\.entity-card-actions\s*\{[^}]*flex-direction:\s*column", mobile_section.group(1)
    ), "Mobile entity card actions flex-direction not found"

    # Check for full width buttons
    assert re.search(
        r"\.btn-edit,\s*\.btn-delete\s*\{[^}]*width:\s*100%", mobile_section.group(1)
    ), "Mobile full-width buttons not found"


def test_subsection_controls_responsive():
    """Test that subsection controls are responsive."""
    html_path = Path("templates/index.html")
    html_content = html_path.read_text()

    # Check for mobile subsection controls styling
    mobile_section = re.search(r"@media\s*\(max-width:\s*767px\)\s*\{(.*?)(?=@media|\Z)", html_content, re.DOTALL)
    assert mobile_section, "Mobile media query section not found"

    # Check for stacked controls
    assert re.search(
        r"\.subsection-controls\s*\{[^}]*flex-direction:\s*column", mobile_section.group(1)
    ), "Mobile subsection controls flex-direction not found"

    # Check for full width search inputs
    assert re.search(
        r'\.subsection-controls\s+input\[type="search"\]\s*\{[^}]*width:\s*100%', mobile_section.group(1)
    ), "Mobile full-width search inputs not found"


def test_landscape_orientation_support():
    """Test that landscape orientation is supported on mobile."""
    html_path = Path("templates/index.html")
    html_content = html_path.read_text()

    # Check for landscape orientation media query
    landscape_query = re.search(r"@media\s*\(max-width:\s*767px\)\s*and\s*\(orientation:\s*landscape\)", html_content)
    assert landscape_query, "Landscape orientation media query not found"
