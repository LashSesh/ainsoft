using System;
using System.Threading.Tasks;
using NativeWebSocket;
using Newtonsoft.Json;
using UnityEngine;

namespace Ainsoft.SeraphicSwarm
{
    public class WebSocketMeshClient
    {
        readonly string _url;
        WebSocket _socket;
        bool _connecting;

        public event Action<MeshSnapshot> OnSnapshot;

        public WebSocketMeshClient(string url)
        {
            _url = url;
        }

        public async void Connect()
        {
            if (_connecting || string.IsNullOrEmpty(_url)) return;
            _connecting = true;
            _socket = new WebSocket(_url);
            _socket.OnOpen += () => Debug.Log($"Mesh websocket connected: {_url}");
            _socket.OnError += msg => Debug.LogError($"Mesh websocket error: {msg}");
            _socket.OnClose += code =>
            {
                Debug.LogWarning($"Mesh websocket closed: {code}");
                _connecting = false;
            };
            _socket.OnMessage += HandleMessage;

            try
            {
                await _socket.Connect();
            }
            catch (Exception ex)
            {
                Debug.LogError($"Failed to connect websocket: {ex.Message}");
                _connecting = false;
            }
        }

        async void HandleMessage(byte[] raw)
        {
            string json = System.Text.Encoding.UTF8.GetString(raw);
            try
            {
                var message = JsonConvert.DeserializeObject<MeshUpdateMessage>(json);
                if (message?.snapshot != null)
                {
                    UnityMainThreadDispatcher.Enqueue(() => OnSnapshot?.Invoke(message.snapshot));
                }
            }
            catch (Exception ex)
            {
                Debug.LogError($"Failed to parse websocket message: {ex.Message}\n{json}");
            }
        }

        public async Task Disconnect()
        {
            if (_socket != null)
            {
                await _socket.Close();
            }
        }

        public void Tick()
        {
#if !UNITY_WEBGL || UNITY_EDITOR
            _socket?.DispatchMessageQueue();
#endif
        }
    }
}
