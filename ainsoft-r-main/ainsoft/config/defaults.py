"""Default configuration values for AinSOFT."""

DEFAULT_TARGET = "127.0.0.1"
DEFAULT_PORT = 8080
DEFAULT_CYCLES = 1
DEFAULT_THRESHOLD = 0.7

DEFAULT_PROXY_CONFIG = {
    "enabled": False,
    "host": None,
    "port": None,
    "username": None,
    "password": None,
}

DEFAULT_PIPELINE_CONFIG = {
    "pipeline": {
        "generators": [
            "ainsoft.pipeline.scorpiosync_generators:fake_api_request_generator",
        ],
        "transformers": [
            "ainsoft.pipeline.scorpiosync_generators:http_builder_transformer",
            "ainsoft.pipeline.scorpiosync_generators:steganography_transformer",
        ],
        "dispatchers": [
            "ainsoft.pipeline.network_dispatcher:network_dispatcher",
        ],
    },
    "fixpunkt": {
        "scorer": "ainsoft.pipeline.triton_scorer:triton_scorer",
        "impulses": [
            "ainsoft.pipeline.scorpiosync_generators:http_builder_transformer",
            "ainsoft.pipeline.scorpiosync_generators:steganography_transformer",
        ],
        "threshold_evaluator": "ainsoft.pipeline.fixpunktattraktor:spectral_threshold_evaluator",
        "threshold_range": [round(i * 0.1, 1) for i in range(1, 10)],
        "dtt": {
            "wt": {"omega": 0.6, "phase": 0.0, "mode": "scaled"},
            "sw": {"omega": 0.45, "phase": 0.3, "mode": "scaled"},
        },
        "resonance_module": {
            "phases": [0.2, 0.4, 0.6],
            "dtt": {"omega": 0.5, "mode": "scaled"},
        },
        "emotion_module": {"valence": 0.0, "arousal": 0.0},
        "consensus": {
            "callable": "ainsoft.pipeline.fixpunktattraktor:mandorla_consensus",
            "kwargs": {"threshold": 0.75},
        },
    },
}

