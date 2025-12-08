# TestRail Reporter Configuration Guide

## Overview

The TestRail Reporter can be configured through environment variables. This document describes all available configuration options and their effects on application behavior.

## Required Configuration

### TestRail Credentials

These variables are required for the application to connect to your TestRail instance:

```bash
# TestRail API endpoint (without trailing slash)
TESTRAIL_BASE_URL=https://your-subdomain.testrail.io

# TestRail user email
TESTRAIL_USER=you@example.com

# TestRail API key (found in TestRail user settings)
TESTRAIL_API_KEY=your_api_key
```

**How to get your API key:**
1. Log into TestRail
2. Click your profile icon → My Settings
3. Navigate to API Keys tab
4. Generate a new API key if needed

## Optional Configuration

### Branding

Customize the application's color scheme:

```bash
# Primary brand color (used for buttons, links, active states)
BRAND_PRIMARY=#2563eb

# Primary hover/active color (darker shade of primary)
BRAND_PRIMARY_600=#1d4ed8

# Background color
BRAND_BG=#0ea5e9

# Background overlay color (with transparency)
BRAND_BG2=#0ea5e91a
```

**Color format:** Hex color codes (e.g., #RRGGBB or #RRGGBBAA for transparency)

### Worker Concurrency

Control parallel processing for different operations:

```bash
# Number of concurrent test run fetches during report generation
RUN_WORKERS=2
RUN_WORKERS_MAX=4
RUN_WORKERS_AUTOSCALE=false

# Number of concurrent attachment downloads
ATTACHMENT_WORKERS=2

# Number of concurrent report generation jobs
REPORT_WORKERS=1
REPORT_WORKERS_MIN=1
REPORT_WORKERS_MAX=4
REPORT_WORKER_IDLE_SECS=120

# Maximum number of completed report jobs to keep in history
REPORT_JOB_HISTORY=60
```

**Recommendations:**
- Keep `RUN_WORKERS` at 2-4 to avoid overwhelming TestRail API
- Set `REPORT_WORKERS=1` for single-user deployments
- Increase `REPORT_WORKERS` for multi-user environments (max 4)
- Higher values may cause rate limiting from TestRail

### Attachment Handling

Configure how attachments are processed in reports:

```bash
# Maximum size for inline attachments (bytes)
ATTACHMENT_INLINE_MAX_BYTES=250000

# Maximum size for inline video attachments (bytes)
ATTACHMENT_VIDEO_INLINE_MAX_BYTES=15000000

# Maximum total attachment size to process (bytes)
ATTACHMENT_MAX_BYTES=520000000

# Maximum image dimension (width or height) in pixels
ATTACHMENT_IMAGE_MAX_DIM=1200

# JPEG compression quality (0-100)
ATTACHMENT_JPEG_QUALITY=65

# Minimum JPEG quality when compressing to meet size limits
ATTACHMENT_MIN_JPEG_QUALITY=40

# Target maximum size for images after compression (bytes)
ATTACHMENT_MAX_IMAGE_BYTES=450000

# Number of retry attempts for failed attachment downloads
ATTACHMENT_RETRY_ATTEMPTS=4
```

**Size Guidelines:**
- 250KB inline limit keeps reports fast to load
- 15MB video limit balances quality and performance
- 520MB total limit prevents memory issues
- 1200px max dimension is good for most displays

**Quality Guidelines:**
- 65 JPEG quality provides good balance
- 40 minimum quality prevents over-compression
- Images are automatically compressed to meet size limits

### Caching

Control how long data is cached to improve performance:

```bash
# Cache TTL for plans list (seconds)
PLANS_CACHE_TTL=180

# Cache TTL for runs list (seconds)
RUNS_CACHE_TTL=60
```

**Recommendations:**
- Shorter TTL = more up-to-date data, more API calls
- Longer TTL = better performance, potentially stale data
- 3 minutes for plans is a good balance
- 1 minute for runs ensures recent test results

### Dashboard Caching

Separate cache configuration for dashboard endpoints:

```bash
# Cache TTL for dashboard plans list (seconds)
DASHBOARD_PLANS_CACHE_TTL=300

# Cache TTL for dashboard plan details (seconds)
DASHBOARD_PLAN_DETAIL_CACHE_TTL=180

# Cache TTL for dashboard statistics (seconds)
DASHBOARD_STATS_CACHE_TTL=120

# Cache TTL for dashboard run statistics (seconds)
DASHBOARD_RUN_STATS_CACHE_TTL=120
```

**Why separate caches?**
- Dashboard makes more expensive calculations
- Longer cache times reduce TestRail API load
- Statistics change less frequently than test results
- Users can manually refresh when needed

**Recommendations:**
- 5 minutes (300s) for plans list is reasonable
- 3 minutes (180s) for plan details balances freshness
- 2 minutes (120s) for statistics is a good default
- Adjust based on your testing cadence

### Dashboard Pagination

Control how many plans are displayed per page:

```bash
# Default number of plans per page
DASHBOARD_DEFAULT_PAGE_SIZE=25

# Maximum number of plans per page (hard limit)
DASHBOARD_MAX_PAGE_SIZE=200
```

**Recommendations:**
- 50 plans per page works well for most projects
- Don't exceed 200 to avoid performance issues
- Smaller page sizes load faster
- Larger page sizes reduce pagination clicks

### Dashboard Visual Thresholds

Configure when visual indicators change color:

```bash
# Pass rate threshold for green color (percentage)
DASHBOARD_PASS_RATE_HIGH=80

# Pass rate threshold for yellow color (percentage)
DASHBOARD_PASS_RATE_MEDIUM=50

# Failure rate threshold for critical badge (percentage)
DASHBOARD_CRITICAL_FAIL_THRESHOLD=20

# Block rate threshold for critical badge (percentage)
DASHBOARD_CRITICAL_BLOCK_THRESHOLD=10
```

**Color Coding:**
- Pass rate ≥ 80%: Green (excellent)
- Pass rate 50-79%: Yellow (needs attention)
- Pass rate < 50%: Red (critical)

**Critical Badges:**
- Shown when failures > 20% OR blocks > 10%
- Pulsing red badge draws immediate attention
- Helps identify problematic plans quickly

**Customization Examples:**
- Strict standards: Set `DASHBOARD_PASS_RATE_HIGH=90`
- Relaxed standards: Set `DASHBOARD_PASS_RATE_MEDIUM=40`
- Sensitive to blocks: Set `DASHBOARD_CRITICAL_BLOCK_THRESHOLD=5`

### Keepalive (Optional)

Prevent service from sleeping on platforms like Railway or Render:

```bash
# URL to ping periodically (leave empty to disable)
KEEPALIVE_URL=

# Interval between keepalive pings (seconds)
KEEPALIVE_INTERVAL=240
```

**When to use:**
- Free tier deployments that sleep after inactivity
- Platforms like Railway, Render, Heroku free tier
- Not needed for always-on deployments

### Memory Logging

Enable periodic memory usage logging:

```bash
# Interval between memory log entries (seconds)
MEM_LOG_INTERVAL=60
```

**Use cases:**
- Debugging memory leaks
- Monitoring resource usage
- Capacity planning
- Set to 0 to disable

### Server Configuration

```bash
# Port for the web server
PORT=8080

# Number of web worker processes (uvicorn/gunicorn)
WEB_CONCURRENCY=1
```

**Important:** Keep `WEB_CONCURRENCY=1` for async job polling to work correctly. Multiple web workers will break the job queue.

## Default TestRail IDs

These configure default values for creating test content:

```bash
# Default suite ID for new runs
DEFAULT_SUITE_ID=1

# Default section ID for new cases
DEFAULT_SECTION_ID=69

# Default template ID for new cases
DEFAULT_TEMPLATE_ID=4

# Default type ID for new cases
DEFAULT_TYPE_ID=7

# Default priority ID for new cases
DEFAULT_PRIORITY_ID=2
```

**How to find these IDs:**
1. Open TestRail in your browser
2. Navigate to the suite/section/etc.
3. Look at the URL: `...&suite_id=1` or `...&section_id=69`
4. Use those numbers in your configuration

## Environment-Specific Configuration

### Development

```bash
# Use shorter cache times for faster feedback
PLANS_CACHE_TTL=30
RUNS_CACHE_TTL=10
DASHBOARD_PLANS_CACHE_TTL=60

# Enable memory logging
MEM_LOG_INTERVAL=30

# Single worker for easier debugging
REPORT_WORKERS=1
RUN_WORKERS=1
```

### Production

```bash
# Longer cache times for better performance
PLANS_CACHE_TTL=300
RUNS_CACHE_TTL=120
DASHBOARD_PLANS_CACHE_TTL=600

# Disable memory logging or use longer interval
MEM_LOG_INTERVAL=300

# More workers for better throughput
REPORT_WORKERS=2
RUN_WORKERS=4
ATTACHMENT_WORKERS=4

# Keepalive if needed
KEEPALIVE_URL=https://your-app.com/healthz
KEEPALIVE_INTERVAL=240
```

### Testing/Staging

```bash
# Balance between dev and prod
PLANS_CACHE_TTL=120
RUNS_CACHE_TTL=60
DASHBOARD_PLANS_CACHE_TTL=180

# Moderate worker counts
REPORT_WORKERS=1
RUN_WORKERS=2
```

## Configuration Validation

The application validates configuration on startup:

- Required variables must be set (TestRail credentials)
- Numeric values must be valid integers
- Negative values are rejected where inappropriate
- Invalid values fall back to defaults with warnings

Check the startup logs for configuration warnings:

```
INFO: REPORT_WORKERS limited to 2 (requested 5, max 4).
```

## Troubleshooting

### "Server missing TestRail credentials"

**Problem:** Required environment variables not set

**Solution:** Set `TESTRAIL_BASE_URL`, `TESTRAIL_USER`, and `TESTRAIL_API_KEY`

### Slow dashboard performance

**Problem:** Too many API calls or large datasets

**Solutions:**
- Increase cache TTLs
- Reduce `DASHBOARD_DEFAULT_PAGE_SIZE`
- Use filters to narrow results
- Increase `RUN_WORKERS` for faster statistics calculation

### Reports timing out

**Problem:** Large reports take too long to generate

**Solutions:**
- Use async report endpoint (POST /api/report)
- Increase `RUN_WORKERS` and `ATTACHMENT_WORKERS`
- Reduce `ATTACHMENT_INLINE_MAX_BYTES`
- Select fewer runs per report

### Memory issues

**Problem:** Application using too much memory

**Solutions:**
- Reduce `ATTACHMENT_MAX_BYTES`
- Reduce `ATTACHMENT_IMAGE_MAX_DIM`
- Reduce `REPORT_JOB_HISTORY`
- Reduce worker counts
- Enable `MEM_LOG_INTERVAL` to monitor usage

### Stale data in dashboard

**Problem:** Dashboard showing old information

**Solutions:**
- Click Refresh button to clear cache
- Reduce cache TTLs
- Check TestRail API is responding
- Verify data has actually changed in TestRail

## Best Practices

1. **Start with defaults:** Only change configuration when needed
2. **Monitor performance:** Use memory logging and health endpoint
3. **Test changes:** Verify configuration changes in staging first
4. **Document customizations:** Keep notes on why you changed defaults
5. **Review periodically:** Revisit configuration as usage patterns change
6. **Use environment files:** Keep `.env` file out of version control
7. **Validate on deploy:** Check startup logs for configuration warnings

## Security Considerations

1. **Never commit credentials:** Keep `.env` file in `.gitignore`
2. **Use environment variables:** Don't hardcode credentials in code
3. **Rotate API keys:** Change TestRail API key periodically
4. **Limit permissions:** Use TestRail user with minimal required permissions
5. **Secure deployment:** Use HTTPS in production
6. **Monitor access:** Review TestRail API usage logs

## Getting Help

If you're unsure about a configuration option:

1. Check this documentation
2. Review the `.env.example` file
3. Check application startup logs
4. Test with default values first
5. Consult TestRail API documentation for ID values

## Configuration Reference

Quick reference table of all variables:

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| TESTRAIL_BASE_URL | string | required | TestRail API endpoint |
| TESTRAIL_USER | string | required | TestRail user email |
| TESTRAIL_API_KEY | string | required | TestRail API key |
| BRAND_PRIMARY | color | #2563eb | Primary brand color |
| BRAND_PRIMARY_600 | color | #1d4ed8 | Primary hover color |
| BRAND_BG | color | #0ea5e9 | Background color |
| BRAND_BG2 | color | #0ea5e91a | Background overlay |
| RUN_WORKERS | int | 2 | Concurrent run fetches |
| RUN_WORKERS_MAX | int | 4 | Maximum run workers |
| ATTACHMENT_WORKERS | int | 2 | Concurrent attachment downloads |
| REPORT_WORKERS | int | 1 | Concurrent report jobs |
| REPORT_WORKERS_MAX | int | 4 | Maximum report workers |
| REPORT_JOB_HISTORY | int | 60 | Report job history size |
| ATTACHMENT_INLINE_MAX_BYTES | int | 250000 | Inline attachment size limit |
| ATTACHMENT_VIDEO_INLINE_MAX_BYTES | int | 15000000 | Inline video size limit |
| ATTACHMENT_MAX_BYTES | int | 520000000 | Total attachment size limit |
| ATTACHMENT_IMAGE_MAX_DIM | int | 1200 | Maximum image dimension |
| ATTACHMENT_JPEG_QUALITY | int | 65 | JPEG compression quality |
| ATTACHMENT_MIN_JPEG_QUALITY | int | 40 | Minimum JPEG quality |
| ATTACHMENT_MAX_IMAGE_BYTES | int | 450000 | Target image size |
| ATTACHMENT_RETRY_ATTEMPTS | int | 4 | Attachment download retries |
| PLANS_CACHE_TTL | int | 180 | Plans cache TTL (seconds) |
| RUNS_CACHE_TTL | int | 60 | Runs cache TTL (seconds) |
| DASHBOARD_PLANS_CACHE_TTL | int | 300 | Dashboard plans cache TTL |
| DASHBOARD_PLAN_DETAIL_CACHE_TTL | int | 180 | Dashboard plan detail cache TTL |
| DASHBOARD_STATS_CACHE_TTL | int | 120 | Dashboard stats cache TTL |
| DASHBOARD_RUN_STATS_CACHE_TTL | int | 120 | Dashboard run stats cache TTL |
| DASHBOARD_DEFAULT_PAGE_SIZE | int | 50 | Default plans per page |
| DASHBOARD_MAX_PAGE_SIZE | int | 200 | Maximum plans per page |
| DASHBOARD_PASS_RATE_HIGH | int | 80 | Green threshold (%) |
| DASHBOARD_PASS_RATE_MEDIUM | int | 50 | Yellow threshold (%) |
| DASHBOARD_CRITICAL_FAIL_THRESHOLD | int | 20 | Critical failure rate (%) |
| DASHBOARD_CRITICAL_BLOCK_THRESHOLD | int | 10 | Critical block rate (%) |
| KEEPALIVE_URL | string | empty | Keepalive ping URL |
| KEEPALIVE_INTERVAL | int | 240 | Keepalive interval (seconds) |
| MEM_LOG_INTERVAL | int | 60 | Memory log interval (seconds) |
| PORT | int | 8080 | Web server port |
| DEFAULT_SUITE_ID | int | 1 | Default suite for runs |
| DEFAULT_SECTION_ID | int | 69 | Default section for cases |
| DEFAULT_TEMPLATE_ID | int | 4 | Default template for cases |
| DEFAULT_TYPE_ID | int | 7 | Default type for cases |
| DEFAULT_PRIORITY_ID | int | 2 | Default priority for cases |
