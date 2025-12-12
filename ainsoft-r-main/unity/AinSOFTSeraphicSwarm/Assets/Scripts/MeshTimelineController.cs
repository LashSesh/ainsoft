using System;
using System.Collections.Generic;
using TMPro;
using UnityEngine;
using UnityEngine.UI;

namespace Ainsoft.SeraphicSwarm
{
    public class MeshTimelineController : MonoBehaviour
    {
        public Slider timelineSlider;
        public Button playButton;
        public Button pauseButton;
        public TMP_Text snapshotLabel;

        readonly List<string> _snapshots = new();
        bool _playState;

        public event Action<string> OnScrub;
        public event Action<bool> OnPlayToggled;

        void Awake()
        {
            if (timelineSlider != null)
            {
                timelineSlider.onValueChanged.AddListener(OnSliderChanged);
            }
            if (playButton != null)
            {
                playButton.onClick.AddListener(() => SetPlayState(true));
            }
            if (pauseButton != null)
            {
                pauseButton.onClick.AddListener(() => SetPlayState(false));
            }
        }

        public void SetSnapshots(IReadOnlyList<string> snapshots)
        {
            _snapshots.Clear();
            if (snapshots != null)
            {
                _snapshots.AddRange(snapshots);
            }
            if (timelineSlider != null)
            {
                timelineSlider.minValue = 0;
                timelineSlider.maxValue = Mathf.Max(0, _snapshots.Count - 1);
                timelineSlider.wholeNumbers = true;
                timelineSlider.value = 0;
            }
            UpdateLabel(0);
        }

        void OnSliderChanged(float value)
        {
            int index = Mathf.Clamp(Mathf.RoundToInt(value), 0, Mathf.Max(0, _snapshots.Count - 1));
            UpdateLabel(index);
            if (index >= 0 && index < _snapshots.Count)
            {
                OnScrub?.Invoke(_snapshots[index]);
            }
        }

        void SetPlayState(bool playing)
        {
            if (_playState == playing) return;
            _playState = playing;
            OnPlayToggled?.Invoke(playing);
        }

        void UpdateLabel(int index)
        {
            if (snapshotLabel == null) return;
            if (_snapshots.Count == 0)
            {
                snapshotLabel.text = "No snapshots";
                return;
            }
            index = Mathf.Clamp(index, 0, _snapshots.Count - 1);
            snapshotLabel.text = _snapshots[index];
        }

        public void HighlightSnapshot(string name)
        {
            int index = _snapshots.IndexOf(name);
            if (index >= 0 && timelineSlider != null)
            {
                timelineSlider.SetValueWithoutNotify(index);
                UpdateLabel(index);
            }
        }
    }
}
