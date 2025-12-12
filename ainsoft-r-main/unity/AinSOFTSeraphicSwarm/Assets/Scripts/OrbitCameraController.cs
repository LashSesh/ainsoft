using UnityEngine;

namespace Ainsoft.SeraphicSwarm
{
    [RequireComponent(typeof(Camera))]
    public class OrbitCameraController : MonoBehaviour
    {
        public Transform target;
        public float distance = 20f;
        public float orbitSpeed = 120f;
        public float panSpeed = 0.5f;
        public float zoomSpeed = 5f;
        public Vector2 pitchLimits = new Vector2(-35f, 80f);

        float _yaw;
        float _pitch;
        Vector3 _targetPosition;

        void Start()
        {
            if (target != null)
            {
                _targetPosition = target.position;
            }
            var angles = transform.eulerAngles;
            _yaw = angles.y;
            _pitch = angles.x;
        }

        void LateUpdate()
        {
            HandleInput();
            Quaternion rotation = Quaternion.Euler(_pitch, _yaw, 0f);
            Vector3 offset = rotation * new Vector3(0f, 0f, -distance);
            transform.position = _targetPosition + offset;
            transform.rotation = rotation;
        }

        void HandleInput()
        {
            if (Input.GetMouseButton(1))
            {
                _yaw += Input.GetAxis("Mouse X") * orbitSpeed * Time.deltaTime;
                _pitch -= Input.GetAxis("Mouse Y") * orbitSpeed * Time.deltaTime;
                _pitch = Mathf.Clamp(_pitch, pitchLimits.x, pitchLimits.y);
            }

            if (Input.GetMouseButton(2))
            {
                Vector3 right = transform.right;
                Vector3 up = transform.up;
                Vector3 pan = (-right * Input.GetAxis("Mouse X") + -up * Input.GetAxis("Mouse Y")) * panSpeed;
                _targetPosition += pan;
            }

            float scroll = Input.GetAxis("Mouse ScrollWheel");
            if (Mathf.Abs(scroll) > Mathf.Epsilon)
            {
                distance = Mathf.Clamp(distance - scroll * zoomSpeed, 5f, 100f);
            }
        }
    }
}
