// Dataset Generator Navigation Fix
// This file handles the Dataset Generator menu functionality

console.log('Dataset navigation script loaded');

document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded, setting up dataset navigation');
    
    // Define the showDatasetView function that the onclick handler expects
    window.showDatasetView = function() {
        console.log('showDatasetView called');
        
        // Hide all other views first
        document.querySelectorAll('#reporterView, #dashboardView, #manageView, #howToView, #datasetView').forEach(view => {
            if (view) view.classList.add('hidden');
        });
        
        // Inject dataset content into the main .content div (like Reporter view)
        const contentDiv = document.querySelector('.content');
        if (contentDiv) {
            // Store original content if needed for restoration
            if (!contentDiv.dataset.originalContent) {
                contentDiv.dataset.originalContent = contentDiv.innerHTML;
            }
            
            // Replace content with dataset generator
            contentDiv.innerHTML = getDatasetGeneratorHTML();
            
            // Set up form handlers
            setupDatasetForm();
        }
        
        const datasetLink = document.getElementById('linkDataset');
        if (datasetLink) {
            // Remove active class from all nav items
            document.querySelectorAll('.nav-item').forEach(item => {
                item.classList.remove('active');
            });
            // Add active class to dataset link
            datasetLink.classList.add('active');
        }
    };
    
    // Function to generate the dataset generator HTML
    function getDatasetGeneratorHTML() {
        return `
            <h1 style="text-align: center; margin-bottom: 8px;">Dataset Generator</h1>
            <p class="subtitle" style="text-align: center; margin-bottom: 24px;">Generate synthetic geospatial datasets for testing purposes.</p>
            
            <div class="grid-panels" style="grid-template-columns: 2fr 1.25fr; gap: 16px; align-items: start;">
                <div class="card">
                    
                    <!-- Dataset Generation Form -->
                    <form id="datasetGenerationForm" style="display: flex; flex-direction: column; gap: 20px;">
                        
                        <!-- Basic Configuration -->
                        <div class="form-section">
                            <h3 style="margin: 0 0 12px; font-size: 16px; color: var(--primary);">📊 Basic Configuration</h3>
                            <div class="form-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px;">
                                <div class="form-group">
                                    <label for="datasetRows" style="display: block; margin: 0 0 6px; font-size: 14px; font-weight: 600; color: var(--text);">
                                        Rows <span style="color: #ef4444;">*</span>
                                    </label>
                                    <input type="number" id="datasetRows" name="rows" value="1000" min="1" max="1000000" required
                                        style="width: 100%; padding: 10px 12px; border: 2px solid var(--border); border-radius: 8px; font-size: 14px;">
                                    <small style="color: var(--muted); font-size: 12px;">1 - 1,000,000 rows</small>
                                </div>
                                <div class="form-group">
                                    <label for="datasetColumns" style="display: block; margin: 0 0 6px; font-size: 14px; font-weight: 600; color: var(--text);">
                                        Columns <span style="color: #ef4444;">*</span>
                                    </label>
                                    <input type="number" id="datasetColumns" name="columns" value="10" min="3" max="35" required
                                        style="width: 100%; padding: 10px 12px; border: 2px solid var(--border); border-radius: 8px; font-size: 14px;">
                                    <small style="color: var(--muted); font-size: 12px;">3 - 35 columns</small>
                                </div>
                                <div class="form-group">
                                    <label for="datasetArea" style="display: block; margin: 0 0 6px; font-size: 14px; font-weight: 600; color: var(--text);">
                                        Geographic Area <span style="color: #ef4444;">*</span>
                                    </label>
                                    <select id="datasetArea" name="area" required
                                        style="width: 100%; padding: 10px 12px; border: 2px solid var(--border); border-radius: 8px; font-size: 14px;">
                                        <option value="Jakarta">Jakarta</option>
                                        <option value="Yogyakarta">Yogyakarta</option>
                                        <option value="Indonesia">Indonesia</option>
                                        <option value="Japan">Japan</option>
                                        <option value="Vietnam">Vietnam</option>
                                    </select>
                                </div>
                            </div>
                        </div>
                        
                        <!-- Geometry Configuration -->
                        <div class="form-section">
                            <h3 style="margin: 0 0 12px; font-size: 16px; color: var(--primary);">🗺️ Geometry Configuration</h3>
                            <div class="form-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px;">
                                <div class="form-group">
                                    <label for="datasetGeometryType" style="display: block; margin: 0 0 6px; font-size: 14px; font-weight: 600; color: var(--text);">
                                        Geometry Type <span style="color: #ef4444;">*</span>
                                    </label>
                                    <select id="datasetGeometryType" name="geometry_type" required
                                        style="width: 100%; padding: 10px 12px; border: 2px solid var(--border); border-radius: 8px; font-size: 14px;">
                                        <option value="POINT">Point</option>
                                        <option value="POLYGON">Polygon</option>
                                        <option value="MULTIPOLYGON">Multi-Polygon</option>
                                        <option value="H3">H3 Hexagon</option>
                                    </select>
                                </div>
                                <div class="form-group">
                                    <label for="datasetFormatType" style="display: block; margin: 0 0 6px; font-size: 14px; font-weight: 600; color: var(--text);">
                                        Format Type <span style="color: #ef4444;">*</span>
                                    </label>
                                    <select id="datasetFormatType" name="format_type" required
                                        style="width: 100%; padding: 10px 12px; border: 2px solid var(--border); border-radius: 8px; font-size: 14px;">
                                        <option value="WKT">WKT (Well-Known Text)</option>
                                        <option value="GEOJSON">GeoJSON</option>
                                    </select>
                                </div>
                            </div>
                        </div>
                        
                        <!-- Data Features -->
                        <div class="form-section">
                            <h3 style="margin: 0 0 12px; font-size: 16px; color: var(--primary);">📈 Data Features</h3>
                            <div class="form-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 16px;">
                                <div class="form-group">
                                    <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;">
                                        <input type="checkbox" id="datasetIncludeDemographic" name="include_demographic" checked
                                            style="width: 18px; height: 18px;">
                                        <span style="font-size: 14px; font-weight: 600; color: var(--text);">Include Demographic Data</span>
                                    </label>
                                    <small style="color: var(--muted); font-size: 12px; margin-left: 26px;">Gender, Occupation, Education Level</small>
                                </div>
                                <div class="form-group">
                                    <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;">
                                        <input type="checkbox" id="datasetIncludeEconomic" name="include_economic" checked
                                            style="width: 18px; height: 18px;">
                                        <span style="font-size: 14px; font-weight: 600; color: var(--text);">Include Economic Data</span>
                                    </label>
                                    <small style="color: var(--muted); font-size: 12px; margin-left: 26px;">Income, Employment, Healthcare Access</small>
                                </div>
                                <div class="form-group">
                                    <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;">
                                        <input type="checkbox" id="datasetUseClustering" name="use_spatial_clustering"
                                            style="width: 18px; height: 18px;">
                                        <span style="font-size: 14px; font-weight: 600; color: var(--text);">Use Spatial Clustering</span>
                                    </label>
                                    <small style="color: var(--muted); font-size: 12px; margin-left: 26px;">Create realistic geographic clusters</small>
                                </div>
                            </div>
                        </div>

                        <!-- Realism Options -->
                        <div class="form-section">
                            <h3 style="margin: 0 0 12px; font-size: 16px; color: var(--primary);">✨ Realism Options</h3>
                            <div class="form-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px;">
                                <div class="form-group">
                                    <label for="datasetDistributionMode" style="display: block; margin: 0 0 6px; font-size: 14px; font-weight: 600; color: var(--text);">
                                        Value Distribution
                                    </label>
                                    <select id="datasetDistributionMode" name="distribution_mode"
                                        style="width: 100%; padding: 10px 12px; border: 2px solid var(--border); border-radius: 8px; font-size: 14px;">
                                        <option value="uniform">Uniform</option>
                                        <option value="normal">Normal</option>
                                        <option value="lognormal">Lognormal</option>
                                        <option value="beta">Beta</option>
                                    </select>
                                </div>
                                <div class="form-group">
                                    <label for="datasetSpatialWeighting" style="display: block; margin: 0 0 6px; font-size: 14px; font-weight: 600; color: var(--text);">
                                        Spatial Weighting
                                    </label>
                                    <select id="datasetSpatialWeighting" name="spatial_weighting"
                                        style="width: 100%; padding: 10px 12px; border: 2px solid var(--border); border-radius: 8px; font-size: 14px;">
                                        <option value="none">None</option>
                                        <option value="urban_bias">Urban Bias</option>
                                        <option value="rural_bias">Rural Bias</option>
                                    </select>
                                </div>
                                <div class="form-group">
                                    <label for="datasetNoiseLevel" style="display: block; margin: 0 0 6px; font-size: 14px; font-weight: 600; color: var(--text);">
                                        Noise Level (0-1)
                                    </label>
                                    <input type="number" id="datasetNoiseLevel" name="noise_level" value="0" min="0" max="1" step="0.01"
                                        style="width: 100%; padding: 10px 12px; border: 2px solid var(--border); border-radius: 8px; font-size: 14px;">
                                </div>
                                <div class="form-group">
                                    <label for="datasetOutlierRate" style="display: block; margin: 0 0 6px; font-size: 14px; font-weight: 600; color: var(--text);">
                                        Outlier Rate (0-1)
                                    </label>
                                    <input type="number" id="datasetOutlierRate" name="outlier_rate" value="0" min="0" max="1" step="0.01"
                                        style="width: 100%; padding: 10px 12px; border: 2px solid var(--border); border-radius: 8px; font-size: 14px;">
                                </div>
                                <div class="form-group">
                                    <label for="datasetOutlierScale" style="display: block; margin: 0 0 6px; font-size: 14px; font-weight: 600; color: var(--text);">
                                        Outlier Scale (>= 1)
                                    </label>
                                    <input type="number" id="datasetOutlierScale" name="outlier_scale" value="2.5" min="1" step="0.1"
                                        style="width: 100%; padding: 10px 12px; border: 2px solid var(--border); border-radius: 8px; font-size: 14px;">
                                </div>
                                <div class="form-group">
                                    <label for="datasetMissingRate" style="display: block; margin: 0 0 6px; font-size: 14px; font-weight: 600; color: var(--text);">
                                        Missing Rate (0-1)
                                    </label>
                                    <input type="number" id="datasetMissingRate" name="missing_rate" value="0" min="0" max="1" step="0.01"
                                        style="width: 100%; padding: 10px 12px; border: 2px solid var(--border); border-radius: 8px; font-size: 14px;">
                                </div>
                                <div class="form-group">
                                    <label for="datasetSeasonality" style="display: block; margin: 0 0 6px; font-size: 14px; font-weight: 600; color: var(--text);">
                                        Seasonality
                                    </label>
                                    <select id="datasetSeasonality" name="seasonality"
                                        style="width: 100%; padding: 10px 12px; border: 2px solid var(--border); border-radius: 8px; font-size: 14px;">
                                        <option value="none">None</option>
                                        <option value="weekday">Weekday Peak</option>
                                        <option value="monthly">Summer Peak</option>
                                    </select>
                                </div>
                                <div class="form-group">
                                    <label for="datasetDateStart" style="display: block; margin: 0 0 6px; font-size: 14px; font-weight: 600; color: var(--text);">
                                        Date Start
                                    </label>
                                    <input type="date" id="datasetDateStart" name="date_start"
                                        style="width: 100%; padding: 10px 12px; border: 2px solid var(--border); border-radius: 8px; font-size: 14px;">
                                </div>
                                <div class="form-group">
                                    <label for="datasetDateEnd" style="display: block; margin: 0 0 6px; font-size: 14px; font-weight: 600; color: var(--text);">
                                        Date End
                                    </label>
                                    <input type="date" id="datasetDateEnd" name="date_end"
                                        style="width: 100%; padding: 10px 12px; border: 2px solid var(--border); border-radius: 8px; font-size: 14px;">
                                </div>
                                <div class="form-group">
                                    <label for="datasetSeed" style="display: block; margin: 0 0 6px; font-size: 14px; font-weight: 600; color: var(--text);">
                                        Seed (Optional)
                                    </label>
                                    <input type="number" id="datasetSeed" name="seed" placeholder="e.g., 1234"
                                        style="width: 100%; padding: 10px 12px; border: 2px solid var(--border); border-radius: 8px; font-size: 14px;">
                                </div>
                            </div>
                            <small style="color: var(--muted); font-size: 12px;">Controls for realism, noise, and temporal patterns.</small>
                        </div>
                        
                        <!-- Advanced Options -->
                        <div class="form-section">
                            <h3 style="margin: 0 0 12px; font-size: 16px; color: var(--primary);">⚙️ Advanced Options</h3>
                            <div class="form-grid" style="display: grid; grid-template-columns: 1fr; gap: 16px;">
                                <div class="form-group">
                                    <label for="datasetGeojsonPath" style="display: block; margin: 0 0 6px; font-size: 14px; font-weight: 600; color: var(--text);">
                                        Land Boundary (GeoJSON)
                                    </label>
                                    <select id="datasetGeojsonPath" name="geojson_path"
                                        style="width: 100%; padding: 10px 12px; border: 2px solid var(--border); border-radius: 8px; font-size: 14px;">
                                        <option value="">None (allow ocean)</option>
                                        <option value="dataset_generator/geoJson/jkt.geojson">Jakarta</option>
                                        <option value="dataset_generator/geoJson/id.json">Indonesia</option>
                                        <option value="dataset_generator/geoJson/jp.json">Japan</option>
                                        <option value="dataset_generator/geoJson/vn.json">Vietnam</option>
                                    </select>
                                    <small style="color: var(--muted); font-size: 12px;">Optional: constrain points to land</small>
                                </div>
                                <div class="form-group">
                                    <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;">
                                        <input type="checkbox" id="datasetStrictLand" name="strict_land"
                                            style="width: 18px; height: 18px;">
                                        <span style="font-size: 14px; font-weight: 600; color: var(--text);">Strict Land-Only</span>
                                    </label>
                                    <small style="color: var(--muted); font-size: 12px; margin-left: 26px;">Fail if land boundaries are missing</small>
                                </div>
                                <div class="form-group">
                                    <label for="datasetFilenamePrefix" style="display: block; margin: 0 0 6px; font-size: 14px; font-weight: 600; color: var(--text);">
                                        Filename Prefix (Optional)
                                    </label>
                                    <input type="text" id="datasetFilenamePrefix" name="filename_prefix" placeholder="e.g., my_custom_dataset"
                                        style="width: 100%; padding: 10px 12px; border: 2px solid var(--border); border-radius: 8px; font-size: 14px;">
                                    <small style="color: var(--muted); font-size: 12px;">Leave empty for auto-generated filename</small>
                                </div>
                            </div>
                        </div>
                        
                        <!-- Submit Button -->
                        <div class="form-actions" style="display: flex; gap: 12px; justify-content: flex-start; padding-top: 20px; border-top: 1px solid var(--border);">
                            <button type="submit" id="generateDatasetBtn" 
                                style="padding: 12px 24px; background: var(--primary); color: white; border: none; border-radius: 8px; font-size: 14px; font-weight: 600; cursor: pointer; transition: all 0.15s ease;">
                                🚀 Generate Dataset
                            </button>
                            <button type="button" id="clearFormBtn"
                                style="padding: 12px 24px; background: transparent; color: var(--muted); border: 2px solid var(--border); border-radius: 8px; font-size: 14px; font-weight: 600; cursor: pointer; transition: all 0.15s ease;">
                                🔄 Reset Form
                            </button>
                        </div>
                    </form>
                    
                    <!-- Generation Results -->
                    <div id="datasetGenerationResults" style="display: none; margin-top: 24px;">
                        <!-- Results will be populated here -->
                    </div>
                    
                </div>
                
                <!-- Right Column - Status and Info -->
                <div class="manage-stack" style="display: flex; flex-direction: column; gap: 12px;">
                    <div class="card">
                        <h2 style="margin: 0 0 8px;">Generation Status</h2>
                        <p style="margin: 0 0 16px; color: var(--muted); font-size: 14px;">Monitor your dataset generation progress here.</p>
                        
                        <!-- Generation Status (moved to right column) -->
                        <div id="datasetGenerationStatus" style="display: none; padding: 16px; border-radius: 8px; border-left: 4px solid var(--primary); background: rgba(26,138,133,0.06);">
                            <div style="display: flex; align-items: center; gap: 12px;">
                                <div class="spinner" style="width: 20px; height: 20px; border: 2px solid rgba(0,0,0,0.1); border-top-color: var(--primary); border-radius: 50%; animation: spin 0.8s linear infinite;"></div>
                                <div>
                                    <strong id="statusTitle">Generating Dataset...</strong>
                                    <p id="statusMessage" style="margin: 4px 0 0; color: var(--muted); font-size: 13px;">Please wait while we generate your dataset.</p>
                                </div>
                            </div>
                        </div>
                        
                        <div id="statusPlaceholder" style="padding: 20px; text-align: center; color: var(--muted); font-size: 14px; border: 2px dashed var(--border); border-radius: 8px;">
                            No active generation jobs
                        </div>
                    </div>
                    
                    <div class="card">
                        <h2 style="margin: 0 0 8px;">Quick Info</h2>
                        <div style="font-size: 13px; color: var(--muted); line-height: 1.5;">
                            <p style="margin: 0 0 8px;"><strong>Supported Formats:</strong> CSV, Excel</p>
                            <p style="margin: 0 0 8px;"><strong>Geometry Types:</strong> Point, Polygon, Multi-Polygon, H3 Hexagon</p>
                            <p style="margin: 0 0 8px;"><strong>Max Rows:</strong> 1,000,000</p>
                            <p style="margin: 0 0 8px;"><strong>Max Columns:</strong> 35</p>
                            <p style="margin: 0;"><strong>Available Areas:</strong> Jakarta, Yogyakarta, Indonesia, Japan, Vietnam</p>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
    
    // Define view switching function
    function showView(viewId) {
        console.log('Switching to view:', viewId);
        
        if (viewId === 'datasetView') {
            // Dataset view is handled by showDatasetView function
            showDatasetView();
            return;
        }
        
        // Restore original content if we're switching away from dataset view
        const contentDiv = document.querySelector('.content');
        if (contentDiv && contentDiv.dataset.originalContent) {
            contentDiv.innerHTML = contentDiv.dataset.originalContent;
            delete contentDiv.dataset.originalContent;
        }
        
        // List of all possible views
        const allViews = ['reporterView', 'dashboardView', 'manageView', 'datasetView', 'howToView'];
        
        // Hide all views
        allViews.forEach(id => {
            const view = document.getElementById(id);
            if (view) {
                view.classList.add('hidden');
            }
        });
        
        // Show target view
        const targetView = document.getElementById(viewId);
        if (targetView) {
            targetView.classList.remove('hidden');
            console.log('Successfully switched to view:', viewId);
        } else {
            console.error('View not found:', viewId);
        }
        
        // Update navigation active states
        document.querySelectorAll('.nav-item').forEach(item => {
            item.classList.remove('active');
        });
    }
    
    // Set up click handlers for all navigation items
    const navItems = {
        'linkReporter': 'reporterView',
        'linkDashboard': 'dashboardView',
        'linkManage': 'manageView',
        'linkHowTo': 'howToView'
    };
    
    Object.entries(navItems).forEach(([linkId, viewId]) => {
        const link = document.getElementById(linkId);
        if (link) {
            // Remove any existing click handlers
            link.onclick = null;
            
            // Add new click handler
            link.addEventListener('click', function(e) {
                e.preventDefault();
                console.log('Navigation clicked:', linkId, '->', viewId);
                showView(viewId);
                this.classList.add('active');
            });
            
            console.log('Click handler added for:', linkId);
        }
    });
    
    // Show reporter view by default
    showView('reporterView');
    const reporterLink = document.getElementById('linkReporter');
    if (reporterLink) {
        reporterLink.classList.add('active');
    }
    
    console.log('Dataset navigation setup complete');
});

// Dataset form handling functions
function setupDatasetForm() {
    console.log('Setting up dataset form handlers');
    
    const form = document.getElementById('datasetGenerationForm');
    const generateBtn = document.getElementById('generateDatasetBtn');
    const clearBtn = document.getElementById('clearFormBtn');
    const statusDiv = document.getElementById('datasetGenerationStatus');
    const resultsDiv = document.getElementById('datasetGenerationResults');
    
    if (!form) {
        console.error('Dataset form not found');
        return;
    }

    const geojsonPaths = {
        Jakarta: 'dataset_generator/geoJson/jkt.geojson',
        Indonesia: 'dataset_generator/geoJson/id.json',
        Japan: 'dataset_generator/geoJson/jp.json',
        Vietnam: 'dataset_generator/geoJson/vn.json'
    };
    const areaSelect = document.getElementById('datasetArea');
    const geojsonSelect = document.getElementById('datasetGeojsonPath');
    if (areaSelect && geojsonSelect) {
        geojsonSelect.value = geojsonPaths[areaSelect.value] || '';
        areaSelect.addEventListener('change', () => {
            geojsonSelect.value = geojsonPaths[areaSelect.value] || '';
        });
    }

    // Form submission handler
    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        console.log('Dataset form submitted');
        
        // Disable form and show loading
        generateBtn.disabled = true;
        generateBtn.textContent = '⏳ Generating...';
        statusDiv.style.display = 'block';
        resultsDiv.style.display = 'none';
        
        // Hide placeholder and show status
        const placeholder = document.getElementById('statusPlaceholder');
        if (placeholder) placeholder.style.display = 'none';
        
        // Collect form data
        const formData = new FormData(form);
        const area = formData.get('area');
        const geojsonPath = formData.get('geojson_path');
        const strictLand = formData.has('strict_land');
        const noiseLevel = parseFloat(formData.get('noise_level'));
        const outlierRate = parseFloat(formData.get('outlier_rate'));
        const outlierScale = parseFloat(formData.get('outlier_scale'));
        const missingRate = parseFloat(formData.get('missing_rate'));
        const seedRaw = formData.get('seed');
        if (strictLand && !geojsonPath) {
            showError('Strict land mode requires a GeoJSON boundary.');
            resetForm();
            return;
        }
        const config = {
            rows: parseInt(formData.get('rows')),
            columns: parseInt(formData.get('columns')),
            geometry_type: formData.get('geometry_type'),
            format_type: formData.get('format_type'),
            area: area,
            include_demographic: formData.has('include_demographic'),
            include_economic: formData.has('include_economic'),
            use_spatial_clustering: formData.has('use_spatial_clustering'),
            geojson_path: geojsonPath ? geojsonPath : null,
            strict_land: strictLand,
            distribution_mode: formData.get('distribution_mode'),
            noise_level: Number.isNaN(noiseLevel) ? 0 : noiseLevel,
            outlier_rate: Number.isNaN(outlierRate) ? 0 : outlierRate,
            outlier_scale: Number.isNaN(outlierScale) ? 2.5 : outlierScale,
            missing_rate: Number.isNaN(missingRate) ? 0 : missingRate,
            spatial_weighting: formData.get('spatial_weighting'),
            seed: seedRaw ? parseInt(seedRaw, 10) : null,
            date_start: formData.get('date_start') || null,
            date_end: formData.get('date_end') || null,
            seasonality: formData.get('seasonality'),
            filename_prefix: formData.get('filename_prefix') || null
        };
        
        console.log('Dataset config:', config);
        
        try {
            // Submit generation request
            const response = await fetch('/api/dataset/generate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(config)
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Failed to start dataset generation');
            }
            
            const job = await response.json();
            console.log('Dataset generation job started:', job);
            
            // Start polling for job status
            pollJobStatus(job.job_id);
            
        } catch (error) {
            console.error('Dataset generation error:', error);
            showError('Failed to generate dataset: ' + error.message);
            resetForm();
        }
    });
    
    // Clear form handler
    clearBtn.addEventListener('click', function() {
        console.log('Clearing dataset form');
        form.reset();
        // Reset to default values
        document.getElementById('datasetRows').value = '1000';
        document.getElementById('datasetColumns').value = '10';
        document.getElementById('datasetArea').value = 'Jakarta';
        document.getElementById('datasetGeometryType').value = 'POINT';
        document.getElementById('datasetFormatType').value = 'WKT';
        document.getElementById('datasetIncludeDemographic').checked = true;
        document.getElementById('datasetIncludeEconomic').checked = true;
        document.getElementById('datasetUseClustering').checked = false;
        document.getElementById('datasetFilenamePrefix').value = '';
        document.getElementById('datasetDistributionMode').value = 'uniform';
        document.getElementById('datasetSpatialWeighting').value = 'none';
        document.getElementById('datasetNoiseLevel').value = '0';
        document.getElementById('datasetOutlierRate').value = '0';
        document.getElementById('datasetOutlierScale').value = '2.5';
        document.getElementById('datasetMissingRate').value = '0';
        document.getElementById('datasetSeasonality').value = 'none';
        document.getElementById('datasetDateStart').value = '';
        document.getElementById('datasetDateEnd').value = '';
        document.getElementById('datasetSeed').value = '';
        document.getElementById('datasetStrictLand').checked = false;
        if (geojsonSelect) {
            geojsonSelect.value = geojsonPaths.Jakarta || '';
        }
        
        // Hide status and results
        statusDiv.style.display = 'none';
        resultsDiv.style.display = 'none';
    });
    
    // Add hover effects to buttons
    generateBtn.addEventListener('mouseenter', function() {
        if (!this.disabled) {
            this.style.transform = 'translateY(-1px)';
            this.style.boxShadow = '0 4px 12px rgba(0, 0, 0, 0.15)';
        }
    });
    
    generateBtn.addEventListener('mouseleave', function() {
        this.style.transform = 'translateY(0)';
        this.style.boxShadow = 'none';
    });
    
    clearBtn.addEventListener('mouseenter', function() {
        this.style.borderColor = 'var(--primary)';
        this.style.color = 'var(--primary)';
    });
    
    clearBtn.addEventListener('mouseleave', function() {
        this.style.borderColor = 'var(--border)';
        this.style.color = 'var(--muted)';
    });
}

async function pollJobStatus(jobId) {
    console.log('Polling job status for:', jobId);
    
    const statusTitle = document.getElementById('statusTitle');
    const statusMessage = document.getElementById('statusMessage');
    const statusDiv = document.getElementById('datasetGenerationStatus');
    const resultsDiv = document.getElementById('datasetGenerationResults');
    
    try {
        const response = await fetch(`/api/dataset/jobs/${jobId}`);
        
        if (!response.ok) {
            throw new Error('Failed to get job status');
        }
        
        const job = await response.json();
        console.log('Job status:', job.status);
        
        // Update status display
        switch (job.status) {
            case 'pending':
                statusTitle.textContent = 'Job Queued...';
                statusMessage.textContent = 'Your dataset generation job is in the queue.';
                break;
            case 'running':
                statusTitle.textContent = 'Generating Dataset...';
                statusMessage.textContent = `Creating ${job.config.rows} rows with ${job.config.columns} columns for ${job.config.area}.`;
                break;
            case 'completed':
                showSuccess(job);
                return;
            case 'failed':
                showError('Dataset generation failed: ' + (job.error_message || 'Unknown error'));
                return;
        }
        
        // Continue polling if job is still running
        if (job.status === 'pending' || job.status === 'running') {
            setTimeout(() => pollJobStatus(jobId), 2000); // Poll every 2 seconds
        }
        
    } catch (error) {
        console.error('Error polling job status:', error);
        showError('Failed to check job status: ' + error.message);
    }
}

function showSuccess(job) {
    console.log('Dataset generation completed:', job);
    
    const statusDiv = document.getElementById('datasetGenerationStatus');
    const resultsDiv = document.getElementById('datasetGenerationResults');
    const placeholder = document.getElementById('statusPlaceholder');
    
    // Hide loading status and show placeholder
    statusDiv.style.display = 'none';
    if (placeholder) placeholder.style.display = 'block';
    
    // Show results
    resultsDiv.style.display = 'block';
    resultsDiv.innerHTML = `
        <div style="padding: 20px; background: #e8f5e8; border-radius: 8px; border-left: 4px solid #28a745;">
            <h3 style="margin: 0 0 12px; color: #28a745;">✅ Dataset Generated Successfully!</h3>
            <p style="margin: 0 0 16px; color: var(--text);">Your dataset has been generated and is ready for download.</p>
            
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; margin-bottom: 16px;">
                <div style="padding: 12px; background: white; border-radius: 6px; border: 1px solid #d1d5db;">
                    <strong style="color: var(--text);">Rows:</strong> ${job.config.rows.toLocaleString()}
                </div>
                <div style="padding: 12px; background: white; border-radius: 6px; border: 1px solid #d1d5db;">
                    <strong style="color: var(--text);">Columns:</strong> ${job.config.columns}
                </div>
                <div style="padding: 12px; background: white; border-radius: 6px; border: 1px solid #d1d5db;">
                    <strong style="color: var(--text);">Area:</strong> ${job.config.area}
                </div>
                <div style="padding: 12px; background: white; border-radius: 6px; border: 1px solid #d1d5db;">
                    <strong style="color: var(--text);">Type:</strong> ${job.config.geometry_type}
                </div>
            </div>
            
            <div style="display: flex; gap: 12px; flex-wrap: wrap;">
                ${job.file_paths.map(path => `
                    <a href="/${path}" download 
                       style="padding: 10px 16px; background: var(--primary); color: white; text-decoration: none; border-radius: 6px; font-weight: 600; transition: all 0.15s ease;"
                       onmouseover="this.style.transform='translateY(-1px)'; this.style.boxShadow='0 4px 12px rgba(0,0,0,0.15)'"
                       onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='none'">
                        📥 Download ${path.split('.').pop().toUpperCase()}
                    </a>
                `).join('')}
            </div>
            
            ${job.validation_results ? `
                <div style="margin-top: 16px; padding: 12px; background: #f0f9ff; border-radius: 6px; border-left: 4px solid #0ea5e9;">
                    <strong style="color: #0ea5e9;">📊 Validation Results:</strong>
                    <pre style="margin: 8px 0 0; font-size: 12px; color: var(--muted); white-space: pre-wrap;">${JSON.stringify(job.validation_results, null, 2)}</pre>
                </div>
            ` : ''}
        </div>
    `;
    
    resetForm();
}

function showError(message) {
    console.error('Dataset generation error:', message);
    
    const statusDiv = document.getElementById('datasetGenerationStatus');
    const resultsDiv = document.getElementById('datasetGenerationResults');
    const placeholder = document.getElementById('statusPlaceholder');
    
    // Hide loading status and show placeholder
    statusDiv.style.display = 'none';
    if (placeholder) placeholder.style.display = 'block';
    
    // Show error
    resultsDiv.style.display = 'block';
    resultsDiv.innerHTML = `
        <div style="padding: 20px; background: #fef2f2; border-radius: 8px; border-left: 4px solid #ef4444;">
            <h3 style="margin: 0 0 12px; color: #ef4444;">❌ Generation Failed</h3>
            <p style="margin: 0; color: var(--text);">${message}</p>
            <button onclick="document.getElementById('datasetGenerationResults').style.display='none'" 
                    style="margin-top: 12px; padding: 8px 16px; background: transparent; color: #ef4444; border: 1px solid #ef4444; border-radius: 6px; cursor: pointer;">
                Dismiss
            </button>
        </div>
    `;
    
    resetForm();
}

function resetForm() {
    const generateBtn = document.getElementById('generateDatasetBtn');
    if (generateBtn) {
        generateBtn.disabled = false;
        generateBtn.textContent = '🚀 Generate Dataset';
    }
}
