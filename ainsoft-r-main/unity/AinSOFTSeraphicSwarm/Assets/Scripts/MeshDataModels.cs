using System;
using System.Collections.Generic;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using UnityEngine;

namespace Ainsoft.SeraphicSwarm
{
    [Serializable]
    public class MeshNode
    {
        public string id;
        [JsonConverter(typeof(Vector3Converter))]
        public Vector3 position;
        public float score;
        public int cluster;
        public Dictionary<string, object> metadata;
    }

    [Serializable]
    public class MeshEdge
    {
        public string id;
        public string source;
        public string target;
        public float weight;
        public Dictionary<string, object> metadata;
    }

    [Serializable]
    public class MeshSnapshot
    {
        public string name;
        public long timestamp;
        public List<MeshNode> nodes;
        public List<MeshEdge> edges;
        public Dictionary<string, object> metadata;
    }

    [Serializable]
    public class MeshUpdateMessage
    {
        public string type;
        public MeshSnapshot snapshot;
    }

    public class Vector3Converter : JsonConverter<Vector3>
    {
        public override void WriteJson(JsonWriter writer, Vector3 value, JsonSerializer serializer)
        {
            writer.WriteStartArray();
            writer.WriteValue(value.x);
            writer.WriteValue(value.y);
            writer.WriteValue(value.z);
            writer.WriteEndArray();
        }

        public override Vector3 ReadJson(JsonReader reader, Type objectType, Vector3 existingValue, bool hasExistingValue, JsonSerializer serializer)
        {
            if (reader.TokenType == JsonToken.StartArray)
            {
                JArray array = JArray.Load(reader);
                float x = array.Count > 0 ? array[0].Value<float>() : 0f;
                float y = array.Count > 1 ? array[1].Value<float>() : 0f;
                float z = array.Count > 2 ? array[2].Value<float>() : 0f;
                return new Vector3(x, y, z);
            }

            if (reader.TokenType == JsonToken.StartObject)
            {
                JObject obj = JObject.Load(reader);
                float x = obj.TryGetValue("x", out var vx) ? vx.Value<float>() : 0f;
                float y = obj.TryGetValue("y", out var vy) ? vy.Value<float>() : 0f;
                float z = obj.TryGetValue("z", out var vz) ? vz.Value<float>() : 0f;
                return new Vector3(x, y, z);
            }

            if (reader.TokenType == JsonToken.String)
            {
                string str = reader.Value.ToString();
                var parts = str.Split(',', ' ');
                if (parts.Length >= 3 &&
                    float.TryParse(parts[0], out float x) &&
                    float.TryParse(parts[1], out float y) &&
                    float.TryParse(parts[2], out float z))
                {
                    return new Vector3(x, y, z);
                }
            }

            return existingValue;
        }
    }
}
