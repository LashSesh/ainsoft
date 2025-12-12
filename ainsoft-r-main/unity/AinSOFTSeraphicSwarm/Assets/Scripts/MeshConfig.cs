using UnityEngine;

namespace Ainsoft.SeraphicSwarm
{
    [CreateAssetMenu(fileName = "MeshConfig", menuName = "AinSOFT/Mesh Config")]
    public class MeshConfig : ScriptableObject
    {
        [Header("Data Sources")]
        public string streamingAssetsSnapshot = "mesh.json";
        public string streamingAssetsSequenceFormat = "mesh_{0:0000}.json";
        [Tooltip("Base URL for websocket streaming (e.g. ws://localhost:8765)")]
        public string websocketUrl = "ws://localhost:8765";
        [Tooltip("Attempt websocket connection on start")]
        public bool connectWebsocketOnStart = true;

        [Header("Animation")]
        [Range(0.1f, 5f)] public float positionLerpSpeed = 2f;
        [Range(0.1f, 5f)] public float colorLerpSpeed = 2f;
        [Range(0f, 1f)] public float windAmplitude = 0.15f;
        [Range(0.05f, 1f)] public float windFrequency = 0.3f;
        public Vector3 windAxis = new Vector3(0.5f, 1f, 0.2f);

        [Header("Visuals")]
        public Gradient clusterGradient;
        public Gradient scoreGradient;
        public AnimationCurve sizeByScore = AnimationCurve.Linear(0f, 0.6f, 1f, 1.4f);
        public float edgeWidth = 0.025f;
        public Color edgeBaseColor = new Color(0.9f, 0.2f, 0.3f, 0.55f);
        public float edgeEmissionMultiplier = 1.5f;

        [Header("Timeline")]
        public float playbackInterval = 1.5f;
        public bool loopPlayback = true;

        [Header("Interaction")]
        public LayerMask selectableLayer;
        public float selectionHighlightScale = 1.15f;
    }
}
