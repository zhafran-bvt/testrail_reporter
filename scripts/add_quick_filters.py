#!/usr/bin/env python3
"""
Script to add Quick Filters and Saved Filters HTML to templates/index.html
"""

# HTML to insert
QUICK_FILTERS_HTML = """
        <!-- Quick Filters -->
        <div class="card" style="margin-bottom: 16px;">
          <h2 style="margin: 0 0 12px;">Quick Filters</h2>
          <div style="display: flex; gap: 8px; flex-wrap: wrap;">
            <button type="button" class="quick-filter-btn" data-filter="today">
              📅 Today
            </button>
            <button type="button" class="quick-filter-btn" data-filter="this-week">
              📆 This Week
            </button>
            <button type="button" class="quick-filter-btn" data-filter="this-month">
              🗓️ This Month
            </button>
            <button type="button" class="quick-filter-btn" data-filter="active">
              ✅ Active Only
            </button>
            <button type="button" class="quick-filter-btn" data-filter="completed">
              ✔️ Completed Only
            </button>
            <button type="button" class="quick-filter-btn" data-filter="clear" style="margin-left: auto;">
              🔄 Clear Filters
            </button>
          </div>
        </div>

        <!-- Saved Filters -->
        <div class="card" style="margin-bottom: 16px;">
          <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px;">
            <h2 style="margin: 0;">Saved Filters</h2>
            <button type="button" id="saveCurrentFilterBtn" class="btn-edit" style="padding: 6px 12px; font-size: 13px;">
              💾 Save Current
            </button>
          </div>
          <select id="savedFiltersDropdown" style="width: 100%; margin-bottom: 12px;">
            <option value="">-- Select a saved filter --</option>
          </select>
          <div id="savedFiltersList" style="display: flex; flex-direction: column; gap: 8px;">
            <!-- Saved filters will appear here -->
          </div>
        </div>

"""

# CSS to add
QUICK_FILTERS_CSS = """
    .quick-filter-btn {
      padding: 8px 16px;
      font-size: 13px;
      border-radius: 8px;
      border: 1px solid var(--border);
      background: transparent;
      color: var(--text);
      cursor: pointer;
      transition: all .15s ease;
      font-weight: 500;
    }

    .quick-filter-btn:hover {
      border-color: var(--primary);
      background: rgba(26, 138, 133, 0.06);
      color: var(--primary);
    }

    .quick-filter-btn.active {
      border-color: var(--primary);
      background: var(--primary);
      color: white;
    }

    .quick-filter-btn:focus {
      outline: 2px solid var(--primary);
      outline-offset: 2px;
    }

    .saved-filter-item {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 10px 12px;
      border: 1px solid var(--border);
      border-radius: 8px;
      background: var(--card-bg);
      transition: border-color .15s ease, box-shadow .15s ease;
    }

    .saved-filter-item:hover {
      border-color: var(--primary);
      box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    }

    .saved-filter-item.default {
      border-color: var(--primary);
      background: rgba(26, 138, 133, 0.06);
    }

    .saved-filter-name {
      font-weight: 600;
      font-size: 13px;
      color: var(--text);
      margin-bottom: 2px;
    }

    .saved-filter-desc {
      font-size: 12px;
      color: var(--muted);
    }

    .saved-filter-actions {
      display: flex;
      gap: 6px;
    }

    .saved-filter-actions button {
      padding: 4px 8px;
      font-size: 11px;
      border-radius: 6px;
      border: 1px solid var(--border);
      background: transparent;
      color: var(--muted);
      cursor: pointer;
      transition: all .15s ease;
    }

    .saved-filter-actions button:hover {
      border-color: var(--primary);
      color: var(--primary);
    }

    .saved-filter-actions button.delete:hover {
      border-color: #ef4444;
      color: #ef4444;
    }
"""


def main():
    template_file = "templates/index.html"

    print(f"Reading {template_file}...")
    with open(template_file, "r", encoding="utf-8") as f:
        content = f.read()

    # Check if already added
    if "Quick Filters" in content and "quick-filter-btn" in content:
        print("✅ Quick Filters HTML already exists in the file!")
        return

    # Find the insertion point (before Sort Controls)
    sort_marker = "<!-- Sort Controls -->"
    if sort_marker not in content:
        print(f"❌ Could not find '{sort_marker}' marker in the file")
        return

    # Insert the HTML
    parts = content.split(sort_marker, 1)
    new_content = parts[0] + QUICK_FILTERS_HTML + "\n        " + sort_marker + parts[1]

    # Find the style section and add CSS
    style_end = "</style>"
    if style_end in new_content:
        style_parts = new_content.split(style_end, 1)
        new_content = style_parts[0] + QUICK_FILTERS_CSS + "\n  " + style_end + style_parts[1]
        print("✅ Added CSS styles")
    else:
        print("⚠️  Could not find </style> tag, CSS not added")

    # Write the updated content
    print(f"Writing updated content to {template_file}...")
    with open(template_file, "w", encoding="utf-8") as f:
        f.write(new_content)

    print("✅ Successfully added Quick Filters and Saved Filters HTML!")
    print("✅ Successfully added CSS styles!")
    print("\n🎉 Integration complete! Refresh your browser at http://localhost:8000")


if __name__ == "__main__":
    main()
