using UnityEngine;

namespace Ainsoft.SeraphicSwarm
{
    [RequireComponent(typeof(LineRenderer))]
    public class MeshEdgeBehaviour : MonoBehaviour
    {
        public MeshEdge Data { get; private set; }
        public bool IsActive { get; private set; }

        LineRenderer _line;
        float _fade;

        void Awake()
        {
            _line = GetComponent<LineRenderer>();
        }

        public void Initialize(MeshEdge edge, Vector3 start, Vector3 end, MeshConfig config)
        {
            Data = edge;
            _line.positionCount = 2;
            _line.SetPosition(0, start);
            _line.SetPosition(1, end);
            _line.widthMultiplier = config.edgeWidth;
            UpdateColor(edge, config, 0f);
            IsActive = true;
            _fade = 0f;
        }

        public void UpdateEdge(MeshEdge edge, Vector3 start, Vector3 end, MeshConfig config)
        {
            Data = edge;
            _line.SetPosition(0, start);
            _line.SetPosition(1, end);
            UpdateColor(edge, config, _fade);
            IsActive = true;
        }

        public void MarkForRemoval()
        {
            IsActive = false;
        }

        public void Tick(MeshConfig config, float deltaTime)
        {
            if (_line == null) return;
            if (IsActive)
            {
                _fade = Mathf.Min(1f, _fade + deltaTime * 3f);
            }
            else
            {
                _fade = Mathf.Max(0f, _fade - deltaTime * 2f);
            }
            _line.widthMultiplier = Mathf.Lerp(_line.widthMultiplier, config.edgeWidth * Mathf.Lerp(0.6f, 1.6f, Mathf.Clamp01(Data.weight)), deltaTime * 2f);
            UpdateColor(Data, config, _fade);
            if (!IsActive && _fade <= 0.001f)
            {
                gameObject.SetActive(false);
            }
        }

        void UpdateColor(MeshEdge edge, MeshConfig config, float fade)
        {
            Color baseColor = config.edgeBaseColor;
            float strength = Mathf.Clamp01(edge != null ? edge.weight : 0.5f);
            Color finalColor = Color.Lerp(baseColor, Color.white, strength * 0.35f);
            finalColor.a *= fade;
            _line.startColor = finalColor;
            _line.endColor = finalColor;
            _line.material.SetColor("_BaseColor", finalColor);
            _line.material.SetColor("_EmissionColor", finalColor * config.edgeEmissionMultiplier * strength);
        }
    }
}
