  
  
RC Flight View: Multi-Firmware and Activity Telemetry Visualization

<img width="974" height="920" alt="image" src="https://github.com/user-attachments/assets/7fd023e4-efdf-4c4a-a822-bf4a6c60b90f" />
  
  
  
RC Flight View is a premium, high-performance telemetry visualization tool for **INAV**, **ArduPilot**, **EdgeTX telemetry**, and **GPX activity** logs. It transforms raw flight and pedestrian data into an interactive 3D environment, allowing for detailed forensic analysis of every maneuver or activity.

### 🛰️ Supported Formwares / Formats
*   **INAV Blackbox**: Full support for `.txt` logs.
*   **ArduPilot DataFlash**: Comprehensive analysis of `.bin` logs.
*   **EdgeTX Telemetry**: Support for `.csv` telemetry log files.
*   **GPX Activity Logs**: Seamless tracking and plotting for `.gpx` logs.


<img width="2003" height="1235" alt="image" src="https://github.com/user-attachments/assets/98892c5e-261d-4c35-b194-c030712cbdf5" />

  
<img width="1406" height="872" alt="image" src="https://github.com/user-attachments/assets/a01dbd2e-3154-4492-bc53-1159c12a8f12" />


  
Key Features:
* Immersive 3D Reconstruction: Experience your flight path in a fully rotatable OpenGL-based viewer, complete with real-time attitude tracking, map overlays, and 3D terrain rendering.
* Intelligent Flag & State Viewer: Instantly decode complex status bitmasks. The dynamic grid highlights active flight modes, sensor health, and navigation states for both INAV and ArduPilot firmwares, filtering out noise to show only what matters for your specific flight.
* Pilot Input Overlay: A transparent, frame-accurate Mode 2 transmitter stick overlay visualizes your actual control inputs directly over the 3D scene, making it easy to correlate pilot actions with aircraft response.
* Streamlined Performance: A custom-optimized startup sequence with an integrated splash screen ensures you go from log selection to data analysis in seconds.
* Zero-Install Portability: Designed for field use, the pre-compiled portable version runs instantly on any Windows machine with no Python dependencies required.


<img width="1241" height="1120" alt="image" src="https://github.com/user-attachments/assets/7ed2c9a0-f88a-49cc-a7aa-1194b5e5dbeb" />


Whether you are tuning PIDs, diagnosing erratic behavior, or simply showcasing your latest long-range mission, RC Flight View provides a powerful, premium interface that makes professional-grade telemetry analysis accessible to everyone.

---

### 🚀 Quick Start
**RC Flight View** is distributed as a zero-install portable application.
1. Download the latest `RC-Flight-View-vXX.zip`.
2. Extract the folder to your preferred location.
3. Run `RC Flight View.exe`.
4. Open your flight log file.

---

### 🗺 Map & Terrain Providers
Data provided by these services is used for non-commercial, forensic analysis purposes:
*   **Satellite Imagery**: [ESRI World Imagery](https://www.esri.com/en-us/arcgis/products/location-services/services/basemaps)
*   **Street Maps**: © [OpenStreetMap](https://www.openstreetmap.org/copyright) contributors
*   **Terrain Data**: [Mapzen Terrarium](https://github.com/tilezen/joerd/blob/master/docs/terrarium.md) via Amazon S3, [OpenTopoData](https://www.opentopodata.org/), and [Open-Elevation](https://open-elevation.com/).

---

### ⚖️ License
**RC Flight View** is open-source software licensed under the **GNU General Public License v3.0 (GPLv3)**.

**Copyright (C) 2026 Fraser Boyd**

> [!IMPORTANT]
> This project is committed to the open-source spirit of the flight controller community. By using the GPLv3, we ensure that the software remains free for all users and that any future improvements made by the community are shared back under the same open terms.

*   **Permissions**: Commercial use, Modification, Distribution, and Private use.
*   **Conditions**: Disclose source, License and copyright notice, Same license (Copyleft).
*   **Limitations**: No Liability, No Warranty.

See the [LICENSE](LICENSE) file for the full legal text.
