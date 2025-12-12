using System;
using System.Collections.Concurrent;
using UnityEngine;

namespace Ainsoft.SeraphicSwarm
{
    public class UnityMainThreadDispatcher : MonoBehaviour
    {
        static readonly ConcurrentQueue<Action> _queue = new();
        static UnityMainThreadDispatcher _instance;

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.BeforeSceneLoad)]
        static void Initialize()
        {
            if (_instance != null) return;
            var obj = new GameObject("UnityMainThreadDispatcher");
            _instance = obj.AddComponent<UnityMainThreadDispatcher>();
            DontDestroyOnLoad(obj);
        }

        public static void Enqueue(Action action)
        {
            if (action == null) return;
            _queue.Enqueue(action);
        }

        void Update()
        {
            while (_queue.TryDequeue(out var action))
            {
                try
                {
                    action?.Invoke();
                }
                catch (Exception ex)
                {
                    Debug.LogError($"Dispatcher action failed: {ex.Message}");
                }
            }
        }
    }
}
