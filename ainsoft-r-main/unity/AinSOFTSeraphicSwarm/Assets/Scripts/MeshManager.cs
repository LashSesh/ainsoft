using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Newtonsoft.Json;
using UnityEngine;

namespace Ainsoft.SeraphicSwarm
{
    public class MeshManager : MonoBehaviour
    {
        [Header("Dependencies")]
        public MeshConfig config;
        public GameObject nodePrefab;
        public GameObject edgePrefab;
        public Camera mainCamera;
        public MeshTimelineController timeline;
        public MeshInteractionController interaction;

        readonly Dictionary<string, MeshNodeBehaviour> _nodes = new();
        readonly Dictionary<string, MeshEdgeBehaviour> _edges = new();
        readonly Dictionary<string, MeshSnapshot> _snapshots = new();
        readonly List<string> _snapshotOrder = new();

        MeshSnapshot _activeSnapshot;
        float _playbackTime;
        bool _isPlaying;

        WebSocketMeshClient _websocket;

        void Awake()
        {
            if (config == null)
            {
                Debug.LogError("MeshConfig reference missing");
            }
            if (timeline != null)
            {
                timeline.OnScrub += HandleTimelineScrub;
                timeline.OnPlayToggled += HandlePlayToggle;
            }
            if (interaction != null)
            {
                interaction.SetManager(this);
            }
        }

        IEnumerator Start()
        {
            yield return LoadInitialSnapshots();
            if (config != null && config.connectWebsocketOnStart)
            {
                _websocket = new WebSocketMeshClient(config.websocketUrl);
                _websocket.OnSnapshot += ApplySnapshot;
                _websocket.Connect();
            }
        }

        void Update()
        {
            _websocket?.Tick();
            float deltaTime = Time.deltaTime;
            foreach (var node in _nodes.Values)
            {
                node.Tick(config, deltaTime, _playbackTime);
            }
            foreach (var edge in _edges.Values)
            {
                edge.Tick(config, deltaTime);
            }

            if (_isPlaying && config != null && _snapshotOrder.Count > 0)
            {
                _playbackTime += deltaTime;
                if (_playbackTime >= config.playbackInterval)
                {
                    _playbackTime = 0f;
                    AdvanceSnapshot();
                }
            }
        }

        public IReadOnlyDictionary<string, MeshNodeBehaviour> Nodes => _nodes;
        public IReadOnlyDictionary<string, MeshEdgeBehaviour> Edges => _edges;

        IEnumerator LoadInitialSnapshots()
        {
            if (config == null)
            {
                yield break;
            }

            string basePath = Path.Combine(Application.streamingAssetsPath, config.streamingAssetsSnapshot);
            if (File.Exists(basePath))
            {
                var snapshot = LoadSnapshotFromFile(basePath);
                if (snapshot != null)
                {
                    CacheSnapshot(snapshot);
                    ApplySnapshot(snapshot);
                }
            }

            // Load sequenced snapshots mesh_0001.json ... until missing
            for (int index = 0; index < 2000; index++)
            {
                string sequenceName = string.Format(config.streamingAssetsSequenceFormat, index);
                string sequencePath = Path.Combine(Application.streamingAssetsPath, sequenceName);
                if (!File.Exists(sequencePath))
                {
                    if (index == 0)
                    {
                        Debug.LogWarning($"No sequenced snapshots found at {sequencePath}");
                    }
                    break;
                }
                var snapshot = LoadSnapshotFromFile(sequencePath);
                if (snapshot != null)
                {
                    CacheSnapshot(snapshot);
                }
                yield return null;
            }

            timeline?.SetSnapshots(_snapshotOrder);
        }

        MeshSnapshot LoadSnapshotFromFile(string path)
        {
            try
            {
                string json = File.ReadAllText(path);
                var snapshot = JsonConvert.DeserializeObject<MeshSnapshot>(json, new JsonSerializerSettings
                {
                    FloatParseHandling = FloatParseHandling.Double
                });
                if (snapshot != null)
                {
                    if (string.IsNullOrEmpty(snapshot.name))
                    {
                        snapshot.name = Path.GetFileNameWithoutExtension(path);
                    }
                    if (snapshot.timestamp == 0)
                    {
                        snapshot.timestamp = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds();
                    }
                }
                return snapshot;
            }
            catch (Exception ex)
            {
                Debug.LogError($"Failed to read snapshot {path}: {ex.Message}");
                return null;
            }
        }

        void CacheSnapshot(MeshSnapshot snapshot)
        {
            if (snapshot == null || string.IsNullOrEmpty(snapshot.name)) return;
            _snapshots[snapshot.name] = snapshot;
            if (!_snapshotOrder.Contains(snapshot.name))
            {
                _snapshotOrder.Add(snapshot.name);
                _snapshotOrder.Sort();
            }
        }

        void AdvanceSnapshot()
        {
            if (_activeSnapshot == null) return;
            int currentIndex = _snapshotOrder.IndexOf(_activeSnapshot.name);
            if (currentIndex < 0) currentIndex = 0;
            int nextIndex = currentIndex + 1;
            if (nextIndex >= _snapshotOrder.Count)
            {
                if (config != null && config.loopPlayback)
                {
                    nextIndex = 0;
                }
                else
                {
                    _isPlaying = false;
                    return;
                }
            }
            string nextName = _snapshotOrder[nextIndex];
            if (_snapshots.TryGetValue(nextName, out var snapshot))
            {
                ApplySnapshot(snapshot);
                timeline?.HighlightSnapshot(nextName);
            }
        }

        void HandleTimelineScrub(string snapshotName)
        {
            if (_snapshots.TryGetValue(snapshotName, out var snapshot))
            {
                _playbackTime = 0f;
                ApplySnapshot(snapshot);
            }
        }

        void HandlePlayToggle(bool playing)
        {
            _isPlaying = playing;
            _playbackTime = 0f;
        }

        public void ApplySnapshot(MeshSnapshot snapshot)
        {
            _activeSnapshot = snapshot;
            var activeNodeIds = new HashSet<string>();
            var activeEdgeIds = new HashSet<string>();

            foreach (var node in snapshot.nodes ?? Enumerable.Empty<MeshNode>())
            {
                activeNodeIds.Add(node.id);
                if (_nodes.TryGetValue(node.id, out var existing))
                {
                    existing.UpdateNode(node, config);
                }
                else
                {
                    var instance = Instantiate(nodePrefab, transform);
                    var behaviour = instance.GetComponent<MeshNodeBehaviour>();
                    behaviour.Initialize(node, config);
                    _nodes[node.id] = behaviour;
                }
            }

            foreach (var kvp in _nodes)
            {
                if (!activeNodeIds.Contains(kvp.Key))
                {
                    kvp.Value.MarkForRemoval();
                }
            }

            foreach (var edge in snapshot.edges ?? Enumerable.Empty<MeshEdge>())
            {
                activeEdgeIds.Add(edge.id);
                if (!_nodes.TryGetValue(edge.source, out var source) || !_nodes.TryGetValue(edge.target, out var target))
                {
                    continue;
                }

                if (_edges.TryGetValue(edge.id, out var existing))
                {
                    existing.UpdateEdge(edge, source.transform.position, target.transform.position, config);
                }
                else
                {
                    var instance = Instantiate(edgePrefab, transform);
                    var behaviour = instance.GetComponent<MeshEdgeBehaviour>();
                    behaviour.Initialize(edge, source.transform.position, target.transform.position, config);
                    _edges[edge.id] = behaviour;
                }
            }

            foreach (var kvp in _edges)
            {
                if (!activeEdgeIds.Contains(kvp.Key))
                {
                    kvp.Value.MarkForRemoval();
                }
            }

            interaction?.OnSnapshotApplied(snapshot);
        }

        public bool TryGetNode(string id, out MeshNodeBehaviour behaviour) => _nodes.TryGetValue(id, out behaviour);
        public bool TryGetEdge(string id, out MeshEdgeBehaviour behaviour) => _edges.TryGetValue(id, out behaviour);
        public MeshSnapshot ActiveSnapshot => _activeSnapshot;
    }
}
