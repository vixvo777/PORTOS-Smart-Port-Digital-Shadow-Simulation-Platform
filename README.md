# PORTOS — Smart Port Digital Shadow & Simulation Platform

**A historical-data-driven platform for maritime activity visualization, 3D geospatial exploration, and port-operation scenario simulation.**

PORTOS is a Smart Port Digital Shadow platform focused on the Port of New Orleans, Louisiana, USA. It brings together historical vessel movement data, interactive 3D visualization, geographic infrastructure layers, and What-If scenario analysis to explore maritime activity and understand potential operational changes.

---

## Overview

Modern ports are complex environments involving vessel traffic, berthing activity, infrastructure, and interconnected operations. Understanding these activities requires combining geographical information, historical observations, and operational analysis.

PORTOS provides a unified environment to explore maritime activity through historical AIS data and an interactive 3D geospatial interface.

The platform aims to help users:

- Visualize historical vessel movements.
- Explore maritime activity in a 3D port environment.
- Navigate geographic infrastructure layers.
- Analyze vessel movement over time.
- Explore hypothetical port-operation scenarios.
- Compare baseline conditions with simulated outcomes.

> **Project scope:** PORTOS currently focuses on historical AIS data and scenario-based analysis. It is not a live vessel-tracking system and does not directly control physical port infrastructure.

## Key Features

### 1. Historical AIS Vessel Tracking

- Historical vessel-position observations.
- Vessel movement visualization.
- Vessel identification using MMSI.
- Position, speed, course, and heading information where available.
- Time-based exploration of vessel tracks.

### 2. 3D Geospatial Visualization

- Interactive 3D environment powered by CesiumJS.
- Geospatial representation of the port environment.
- Vessel-position visualization.
- Geographic layers using GeoJSON.
- Interactive camera and scene navigation.

### 3. Historical Vessel Playback

- Explore vessel activity across the available historical period.
- Navigate through recorded vessel positions.
- Visualize vessel movement using timestamps.
- Inspect individual vessel trajectories.

### 4. Port Activity Analysis

- Explore vessel activity and spatial patterns.
- Analyze available port-call information.
- Examine vessel movements and geographical relationships.
- Support operational understanding through visual analytics.

### 5. What-If Scenario Simulation

PORTOS aims to support hypothetical operational scenarios, including:

- Increased vessel traffic.
- Temporary berth unavailability.
- Increased vessel handling time.
- Port capacity expansion.

These scenarios allow users to explore possible operational impacts and compare modeled outcomes with a baseline.

**Note:** What-If results are simulated outputs, not actual historical events or guaranteed predictions.

---

## Dataset

### Historical AIS Data

The project uses historical Automatic Identification System (AIS) data for the New Orleans region.

| Attribute | Details |
|---|---|
| Study area | New Orleans, Louisiana, USA |
| Historical period | June 15–16, 2019 |
| Reported AIS records | 651,044 |
| Reported unique vessels | 477 |
| Data format | Compressed CSV |
| Data type | Historical vessel-position observations |

**Dataset file:**

`smartport_backend/data/source/ais/new_orleans_ais_2019-06-15_16_clean.csv.gz`

### AIS Parameters

The dataset includes fields such as:

| Parameter | Description |
|---|---|
| MMSI | Maritime Mobile Service Identity |
| Base Date Time | Timestamp of the AIS observation |
| Longitude | Vessel longitude |
| Latitude | Vessel latitude |
| SOG | Speed Over Ground |
| COG | Course Over Ground |
| Heading | Vessel heading |
| Navigation Status | Reported navigation status |
| Vessel Name | Vessel name, where available |
| Vessel Type | Vessel classification |
| Vessel Length | Vessel length, where available |
| Width | Vessel width, where available |
| Draft | Vessel draft, where available |

Additional track-related fields may include track segments and time-gap information.

### Geographic Data

PORTOS uses GeoJSON layers to represent geographic features in the visualization environment.

Geographic datasets must be interpreted according to their original source and spatial coverage. Not every geographic layer should be treated as an official New Orleans port boundary or berth location.

---

## Technology Stack

The project architecture uses the following technologies:

| Technology | Purpose |
|---|---|
| CesiumJS | 3D geospatial visualization |
| JavaScript / TypeScript | Frontend development |
| Python | Backend and data processing |
| Pandas | AIS data processing |
| GeoJSON | Geographic data representation |
| REST API | Frontend-backend communication |

*The exact installed dependencies and versions should be checked against the repository's dependency files.*

---

## System Architecture

The platform follows a data-processing and visualization workflow:

```text
       Historical AIS Dataset
                 |
                 v
       Python Data Processing
                 |
                 v
          Backend REST API
                 |
                 v
        Frontend Application
                 |
                 v
             CesiumJS
                 |
          +------+------+
          |             |
          v             v
     Vessel Tracks   GeoJSON Layers
          |             |
          +------+------+
                 |
                 v
       Historical 3D Visualization
                 |
                 v
       What-If Scenario Analysis
```

### Data Flow

1. Historical AIS records are loaded and processed.
2. The backend provides vessel information and track data through API endpoints.
3. The frontend requests the required data.
4. CesiumJS visualizes vessels and geographic layers.
5. Historical timestamps drive vessel playback.
6. Scenario analysis explores hypothetical operational changes.

---

## API Reference

The following endpoints are part of the discussed backend implementation. Confirm their availability and parameters against the current source code.

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/v1/ais/coverage` | Returns AIS dataset coverage information |
| GET | `/api/v1/ais/tracks` | Retrieves vessel tracks for a selected time range |
| GET | `/api/v1/ais/track/{mmsi}` | Retrieves a specific vessel's track |

### Example API Requests

```http
GET /api/v1/ais/coverage
```

```http
GET /api/v1/ais/tracks?start=2019-06-15T00:00:00&end=2019-06-16T23:59:59
```

```http
GET /api/v1/ais/track/123456789?start=2019-06-15T00:00:00&end=2019-06-16T23:59:59
```

---

## Digital Shadow Approach

PORTOS follows a **Digital Shadow** approach.

A Digital Shadow provides a digital representation of a physical environment using data collected from that environment. The information flow is primarily from the physical environment to the digital representation.

In PORTOS:

- Historical AIS observations represent vessel activity.
- CesiumJS provides the spatial visualization.
- Geographic layers provide contextual infrastructure information.
- What-If scenarios explore hypothetical operational changes.

The current system does not establish continuous bidirectional communication with physical port infrastructure. Therefore, PORTOS should not be described as a fully connected, real-time Digital Twin.

---

## Future Development Roadmap

The following improvements are planned development directions.

### Phase 1 — Data Reliability

- [ ] Improve AIS data validation.
- [ ] Handle missing and invalid coordinates.
- [ ] Improve timestamp consistency.
- [ ] Prevent interpolation across large observation gaps.
- [ ] Preserve vessel track segments during playback.
- [ ] Document dataset sources and licenses.

### Phase 2 — 3D Visualization

- [ ] Improve vessel models and visual differentiation.
- [ ] Improve camera navigation.
- [ ] Add detailed vessel information panels.
- [ ] Improve historical timeline synchronization.
- [ ] Add vessel-type filters.
- [ ] Improve geographic layer styling.

### Phase 3 — Port Analytics

- [ ] Improve vessel arrival and departure analysis.
- [ ] Develop reliable port-call identification.
- [ ] Improve berth and anchorage activity analysis.
- [ ] Add vessel traffic density visualization.
- [ ] Develop operational KPI dashboards.

### Phase 4 — Simulation Engine

- [ ] Improve What-If scenario configuration.
- [ ] Add configurable vessel traffic demand.
- [ ] Model berth availability.
- [ ] Model vessel handling times.
- [ ] Add queue and waiting-time analysis.
- [ ] Compare baseline and simulated KPIs.
- [ ] Validate simulation assumptions.

### Phase 5 — Performance and Reliability

- [ ] Optimize large AIS dataset queries.
- [ ] Improve backend error handling.
- [ ] Add automated API tests.
- [ ] Add frontend testing.
- [ ] Improve application performance.
- [ ] Add Docker-based deployment support.
- [ ] Document reproducible setup instructions.

### Phase 6 — Future Data Integration

- [ ] Investigate live AIS feed integration.
- [ ] Explore additional port infrastructure datasets.
- [ ] Investigate weather and environmental data integration.
- [ ] Explore external port-operation data sources.
- [ ] Investigate more advanced digital-shadow capabilities.

---

## Known Limitations

- The current AIS dataset represents historical observations, not live vessel positions.
- AIS coverage is limited to the available dataset and study period.
- Geographic layers depend on the source datasets and their spatial accuracy.
- Inferred berth or port-call information requires validation.
- What-If results depend on simulation assumptions and input parameters.
- The platform does not directly control real-world port infrastructure.

---

## Installation and Setup

The installation instructions should match the current repository structure and dependency files.

Before running the project, ensure that the required Python and Node.js environments are installed.

### Backend

Navigate to the backend directory:

```bash
cd smartport_backend
```

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it on Windows:

```powershell
.venv\Scripts\activate
```

Install the dependencies using the repository's dependency file:

```bash
pip install -r requirements.txt
```

### Frontend

Navigate to the frontend directory (use the actual frontend path in the repository):

```bash
cd frontend
```

Install dependencies:

```bash
npm install
```

Start the development server using the configured project script:

```bash
npm run dev
```

*Backend startup commands, environment variables, and frontend directory names must be verified against the current repository before use.*

---

## Contributing

Contributions, suggestions, and improvements are welcome.

1. Fork the repository.
2. Create a feature branch.
3. Implement your changes.
4. Test your changes.
5. Submit a pull request with a clear description.

Areas where contributions are particularly useful:

- AIS data processing.
- 3D geospatial visualization.
- Historical playback.
- Port activity analytics.
- Scenario simulation.
- Performance optimization.

---

## Project Information

**Project Name:** PORTOS — Smart Port Digital Shadow & Simulation Platform

**Study Area:** New Orleans, Louisiana, USA

**Project Focus:** Historical Maritime Data, 3D Geospatial Visualization, Port Analytics, and What-If Simulation.

**Repository:** [PORTOS on GitHub](https://github.com/vixvo777/PORTOS-Smart-Port-Digital-Shadow-Simulation-Platform)

---

*PORTOS explores how historical maritime data and geospatial technologies can support smarter port monitoring, visualization, and operational analysis.*
