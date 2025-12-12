# AinSOFT Seraphic Swarm Unity Visualization

This Unity project visualizes AinSOFT mesh exports and live websocket updates with organic, glass-like aesthetics.

## Requirements
- Unity 2022.3 LTS (URP)
- Newtonsoft Json package (install via UPM or NuGet)
- Websocket client (e.g. `NativeWebSocket` or `BestHTTP`)

## Setup
1. Open the project in Unity 2022.3 LTS.
2. Install packages via Package Manager:
   - Universal RP (already referenced)
   - TextMeshPro
   - `com.cysharp.websockets` or `NativeWebSocket`
   - Newtonsoft Json (com.unity.nuget.newtonsoft-json)
3. Create URP pipeline asset and assign it in Project Settings → Graphics.
4. Create materials and assign them to the node/edge prefabs.

## Scene Configuration
- Create an empty scene `SeraphicSwarm` with neutral dark background.
- Add global volume and lighting for subtle crystal ambience.
- Place the `MeshManager` prefab (empty GameObject with manager scripts) into the scene.
- Add UI Canvas for timeline slider, play/pause buttons, and info panel.

## Streaming Assets
Place initial `mesh.json` snapshots under `Assets/StreamingAssets/` (or configure via inspector) and optional sequenced files `mesh_0001.json`, `mesh_0002.json`, etc.

## Play Mode
- On play, the manager loads the first snapshot, animates nodes/edges, and optionally connects to the websocket at `ws://localhost:8765`.
- Use the timeline UI to scrub or autoplay snapshots.
- Click nodes/edges to inspect metadata in the info panel.

All scripts are located in `Assets/Scripts`.
