using System.Text;
using TMPro;
using UnityEngine;
using UnityEngine.EventSystems;

namespace Ainsoft.SeraphicSwarm
{
    public class MeshInteractionController : MonoBehaviour
    {
        public MeshConfig config;
        public Camera sceneCamera;
        public CanvasGroup infoPanel;
        public TMP_Text infoText;

        MeshManager _manager;
        Transform _highlight;
        Vector3 _originalScale;

        public void SetManager(MeshManager manager)
        {
            _manager = manager;
        }

        void Update()
        {
            if (sceneCamera == null || EventSystem.current != null && EventSystem.current.IsPointerOverGameObject())
            {
                return;
            }

            if (Input.GetMouseButtonDown(0))
            {
                Ray ray = sceneCamera.ScreenPointToRay(Input.mousePosition);
                if (Physics.Raycast(ray, out var hit, 1000f, config.selectableLayer))
                {
                    HandleSelection(hit.collider.GetComponentInParent<MeshNodeBehaviour>(), hit.collider.GetComponentInParent<MeshEdgeBehaviour>());
                }
            }
        }

        void HandleSelection(MeshNodeBehaviour node, MeshEdgeBehaviour edge)
        {
            if (node != null)
            {
                Highlight(node.transform);
                ShowInfo(FormatNodeInfo(node));
            }
            else if (edge != null)
            {
                Highlight(edge.transform);
                ShowInfo(FormatEdgeInfo(edge));
            }
        }

        void Highlight(Transform target)
        {
            if (_highlight != null)
            {
                _highlight.localScale = _originalScale;
            }
            _highlight = target;
            if (_highlight != null)
            {
                _originalScale = _highlight.localScale;
                _highlight.localScale = _originalScale * config.selectionHighlightScale;
            }
        }

        void ShowInfo(string text)
        {
            if (infoText != null)
            {
                infoText.text = text;
            }
            if (infoPanel != null)
            {
                infoPanel.alpha = 1f;
                infoPanel.blocksRaycasts = true;
            }
        }

        string FormatNodeInfo(MeshNodeBehaviour node)
        {
            var sb = new StringBuilder();
            sb.AppendLine($"Node: {node.Data.id}");
            sb.AppendLine($"Score: {node.Data.score:0.000}");
            sb.AppendLine($"Cluster: {node.Data.cluster}");
            sb.AppendLine($"Position: {node.Data.position}");
            if (node.Data.metadata != null)
            {
                foreach (var kv in node.Data.metadata)
                {
                    sb.AppendLine($"{kv.Key}: {kv.Value}");
                }
            }
            return sb.ToString();
        }

        string FormatEdgeInfo(MeshEdgeBehaviour edge)
        {
            var sb = new StringBuilder();
            sb.AppendLine($"Edge: {edge.Data.id}");
            sb.AppendLine($"Source: {edge.Data.source}");
            sb.AppendLine($"Target: {edge.Data.target}");
            sb.AppendLine($"Weight: {edge.Data.weight:0.000}");
            if (edge.Data.metadata != null)
            {
                foreach (var kv in edge.Data.metadata)
                {
                    sb.AppendLine($"{kv.Key}: {kv.Value}");
                }
            }
            return sb.ToString();
        }

        public void OnSnapshotApplied(MeshSnapshot snapshot)
        {
            if (infoPanel != null)
            {
                infoPanel.alpha = 0.75f;
                infoPanel.blocksRaycasts = false;
            }
        }
    }
}
