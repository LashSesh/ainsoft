using System.Collections.Generic;
using UnityEngine;

namespace Ainsoft.SeraphicSwarm
{
    [RequireComponent(typeof(Renderer))]
    public class MeshNodeBehaviour : MonoBehaviour
    {
        public MeshNode Data { get; private set; }
        public Vector3 TargetPosition { get; private set; }
        public float TargetScale { get; private set; } = 1f;
        public Color TargetColor { get; private set; } = Color.white;
        public bool IsActive { get; private set; }

        Renderer _renderer;
        MaterialPropertyBlock _propBlock;
        Vector3 _noiseSeed;
        float _fade = 0f;

        void Awake()
        {
            _renderer = GetComponent<Renderer>();
            _propBlock = new MaterialPropertyBlock();
            _noiseSeed = new Vector3(Random.value * 10f, Random.value * 10f, Random.value * 10f);
        }

        public void Initialize(MeshNode node, MeshConfig config)
        {
            Data = node;
            TargetPosition = node.position;
            TargetScale = config.sizeByScore.Evaluate(node.score);
            TargetColor = EvaluateColor(node, config);
            transform.position = TargetPosition;
            transform.localScale = Vector3.one * TargetScale;
            UpdateMaterial(TargetColor, 0f);
            IsActive = true;
            _fade = 0f;
        }

        public void UpdateNode(MeshNode node, MeshConfig config)
        {
            Data = node;
            TargetPosition = node.position;
            TargetScale = config.sizeByScore.Evaluate(node.score);
            TargetColor = EvaluateColor(node, config);
            IsActive = true;
        }

        public void MarkForRemoval()
        {
            IsActive = false;
        }

        public void Tick(MeshConfig config, float deltaTime, float playbackAlpha)
        {
            if (_renderer == null) return;

            float lerpPos = Mathf.Clamp01(config.positionLerpSpeed * deltaTime);
            float lerpCol = Mathf.Clamp01(config.colorLerpSpeed * deltaTime);

            Vector3 wind = ComputeWind(config, Time.time + playbackAlpha);
            transform.position = Vector3.Lerp(transform.position, TargetPosition + wind, lerpPos);
            float scale = Mathf.Lerp(transform.localScale.x, TargetScale, lerpCol);
            transform.localScale = Vector3.one * scale;

            if (IsActive)
            {
                _fade = Mathf.Min(1f, _fade + deltaTime * 3f);
            }
            else
            {
                _fade = Mathf.Max(0f, _fade - deltaTime * 2f);
            }

            Color currentColor = Color.Lerp(GetCurrentColor(), TargetColor, lerpCol);
            UpdateMaterial(currentColor, _fade);
        }

        Color EvaluateColor(MeshNode node, MeshConfig config)
        {
            Color clusterColor = config.clusterGradient != null
                ? config.clusterGradient.Evaluate(Mathf.Repeat(node.cluster * 0.123f, 1f))
                : Color.white;
            Color scoreColor = config.scoreGradient != null
                ? config.scoreGradient.Evaluate(Mathf.Clamp01(node.score))
                : Color.Lerp(Color.cyan, Color.magenta, node.score);
            return Color.Lerp(clusterColor, scoreColor, 0.5f);
        }

        Vector3 ComputeWind(MeshConfig config, float t)
        {
            float noise = Mathf.PerlinNoise(_noiseSeed.x + t * config.windFrequency, _noiseSeed.y + t * config.windFrequency);
            return config.windAxis.normalized * (noise - 0.5f) * 2f * config.windAmplitude;
        }

        Color GetCurrentColor()
        {
            if (_renderer == null) return Color.white;
            _renderer.GetPropertyBlock(_propBlock);
            return _propBlock.GetColor("_BaseColor");
        }

        void UpdateMaterial(Color color, float fade)
        {
            _renderer.GetPropertyBlock(_propBlock);
            Color finalColor = color;
            finalColor.a = Mathf.Clamp01(fade);
            _propBlock.SetColor("_BaseColor", finalColor);
            _propBlock.SetFloat("_Surface", 1f);
            _propBlock.SetFloat("_AlphaClip", 0f);
            _propBlock.SetFloat("_Smoothness", 0.85f);
            _propBlock.SetFloat("_Emission", Mathf.Lerp(0.1f, 1.2f, Data != null ? Mathf.Clamp01(Data.score) : 0.5f));
            _renderer.SetPropertyBlock(_propBlock);
            if (!IsActive && fade <= 0.001f)
            {
                gameObject.SetActive(false);
            }
        }
    }
}
