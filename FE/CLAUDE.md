# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Static HTML/JS frontend for iPoor MIS. No build step required - all pages are vanilla HTML with inline CSS and JavaScript. Served via nginx in Docker.

## Development

### Local Development

Open HTML files directly in browser, or use any static server:
```bash
python -m http.server 3000
# or
npx serve -p 3000
```

### Docker

```bash
docker build -t ipoor-fe .
docker run -p 3000:80 ipoor-fe
```

### API Configuration

Edit `config.js` to change API base URL:
- Localhost auto-detects `http://127.0.0.1:8000`
- Production uses `https://ipoor.hanzomaster.dev/api`
- Override by setting `window.IPOOR_API_BASE` before scripts load

## Architecture

### Page Structure

```
FE/
├── config.js         # API base URL configuration (auto-detects environment)
├── nginx.conf        # Production nginx config (proxies /api/ to backend)
├── Auth/             # Authentication pages
│   ├── Login.html
│   ├── Signup.html
│   └── ForgotPassword.html
├── HomePage/         # Authenticated dashboard pages
│   ├── HomePage.html        # Main dashboard with stats
│   ├── HouseholdList.html   # Household listing
│   ├── HouseholdDetail.html
│   ├── HouseholdEdit.html
│   ├── HouseholdNew.html
│   ├── PolicyList.html      # Policy management
│   ├── PolicyDetail.html
│   ├── PolicyForm.html
│   ├── GISMap.html          # Geographic visualization
│   ├── DataCollection.html  # Survey data management
│   └── ActivityLogs.html    # Audit trail
├── LandingPage/      # Public pages (no auth required)
│   ├── index.html           # Landing page
│   ├── GISPublic.html       # Public GIS map
│   ├── NewsPublic.html      # Public news/policies
│   └── PolicyPublicDetail.html
├── data/             # Static data files
│   ├── communes.js          # Commune dropdown data
│   ├── ethnicities.js       # Ethnicity dropdown data
│   └── processed/           # GIS data (used by backend)
│       ├── gis_indicator_values.csv
│       └── region_map.json
└── assets/           # Images and static assets
```

### Authentication Pattern

All authenticated pages follow this pattern:
1. Check for `ipoor_access_token` in localStorage/sessionStorage
2. If missing/expired, redirect to `/Auth/Login.html`
3. Send JWT in `Authorization: Bearer <token>` header

Storage behavior:
- "Remember me" checked: localStorage
- "Remember me" unchecked: sessionStorage

### API Calls Pattern

All pages use fetch with this pattern:
```javascript
const API_BASE = window.IPOOR_API_BASE;
const token = localStorage.getItem('ipoor_access_token') || sessionStorage.getItem('ipoor_access_token');

fetch(`${API_BASE}/endpoint`, {
    headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
    }
})
```

### Nginx Proxy

In production, nginx proxies `/api/` to the backend container:
- `/api/households` -> `http://ipoor_api:8000/households`
- Static files served directly from nginx

### Styling

- All CSS is inline in each HTML file (no shared stylesheets)
- Design system uses CSS custom properties (`:root` variables)
- Primary colors: navy (`#0F172A`), blue (`#3b82f6`)
- Fonts: Inter (auth pages), Manrope (dashboard)

### GIS Data

`data/processed/` contains geographic data consumed by the backend API:
- `gis_indicator_values.csv` - Indicator values by region
- `region_map.json` - Geographic boundaries

These files are copied into the backend Docker image during build.
