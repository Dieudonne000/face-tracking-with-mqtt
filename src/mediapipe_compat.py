"""
MediaPipe face mesh compatibility layer.

MediaPipe 0.10.28+ removed the legacy `mediapipe.solutions.face_mesh` API.
This module provides a single interface that works with both:
- Old API: mp.solutions.face_mesh.FaceMesh (if available)
- New API: mediapipe.tasks.python.vision.FaceLandmarker (Tasks API)

Usage:
    from src.mediapipe_compat import get_face_mesh
    mesh = get_face_mesh()
    res = mesh.process(rgb_numpy_array)  # RGB, HxWx3, uint8
    if res.multi_face_landmarks:
        lm = res.multi_face_landmarks[0].landmark  # list-like of .x, .y, .z
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any, List, Optional

import numpy as np

# Project root (parent of src/)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_MODEL_DIR = _PROJECT_ROOT / "models"
_FACE_LANDMARKER_TASK = _MODEL_DIR / "face_landmarker.task"
_FACE_LANDMARKER_URL = (
    "https://storage.googleapis.com/mediapipe-models/face_landmarker/"
    "face_landmarker/float16/1/face_landmarker.task"
)

_face_mesh_impl: Optional[Any] = None
_use_tasks_api: Optional[bool] = None


def _has_solutions_api() -> bool:
    try:
        import mediapipe as mp
        return hasattr(mp, "solutions") and hasattr(mp.solutions, "face_mesh")
    except Exception:
        return False


def _create_legacy_face_mesh():
    """Create FaceMesh using the old solutions API."""
    import mediapipe as mp
    return mp.solutions.face_mesh.FaceMesh(
        static_image_mode=False,
        max_num_faces=1,
        refine_landmarks=True,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    )


def _download_face_landmarker_task() -> Path:
    """Download face_landmarker.task to models/ if not present."""
    _MODEL_DIR.mkdir(parents=True, exist_ok=True)
    if _FACE_LANDMARKER_TASK.is_file():
        return _FACE_LANDMARKER_TASK
    try:
        import urllib.request
        print(f"[mediapipe_compat] Downloading face_landmarker.task to {_FACE_LANDMARKER_TASK} ...")
        urllib.request.urlretrieve(_FACE_LANDMARKER_URL, _FACE_LANDMARKER_TASK)
        print("[mediapipe_compat] Download done.")
    except Exception as e:
        raise RuntimeError(
            f"Failed to download face_landmarker.task from {_FACE_LANDMARKER_URL}. "
            f"Download it manually and place it at {_FACE_LANDMARKER_TASK}. Error: {e}"
        ) from e
    return _FACE_LANDMARKER_TASK


def _create_tasks_face_mesh():
    """Create a wrapper around FaceLandmarker that mimics the old process() -> multi_face_landmarks API."""
    model_path = _download_face_landmarker_task()

    from mediapipe.tasks.python.core import base_options as base_options_lib
    from mediapipe.tasks.python.vision import face_landmarker as face_landmarker_lib
    from mediapipe.tasks.python.vision.core import image as image_lib
    from mediapipe.tasks.python.vision.core import vision_task_running_mode as running_mode_lib

    BaseOptions = base_options_lib.BaseOptions
    FaceLandmarker = face_landmarker_lib.FaceLandmarker
    FaceLandmarkerOptions = face_landmarker_lib.FaceLandmarkerOptions
    Image = image_lib.Image
    ImageFormat = image_lib.ImageFormat
    VisionTaskRunningMode = running_mode_lib.VisionTaskRunningMode

    options = FaceLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=str(model_path)),
        running_mode=VisionTaskRunningMode.IMAGE,
        num_faces=1,
        min_face_detection_confidence=0.5,
        min_face_presence_confidence=0.5,
    )
    landmarker = FaceLandmarker.create_from_options(options)

    class _TasksResultAdapter:
        """Mimics old FaceMesh process() result: .multi_face_landmarks = [face0], face0.landmark = list of .x/.y/.z."""

        def __init__(self, face_landmarks: List[List[Any]]):
            # face_landmarks: List[List[NormalizedLandmark]]
            self.multi_face_landmarks = []
            for one_face in face_landmarks:
                # Old API: landmark is a list-like of objects with .x, .y, .z
                landmark_list = [SimpleNamespace(x=p.x, y=p.y, z=getattr(p, "z", 0.0)) for p in one_face]
                self.multi_face_landmarks.append(SimpleNamespace(landmark=landmark_list))

    class _TasksFaceMeshWrapper:
        def process(self, rgb: np.ndarray) -> _TasksResultAdapter:
            if rgb.dtype != np.uint8 or rgb.ndim != 3 or rgb.shape[2] != 3:
                rgb = np.asarray(rgb, dtype=np.uint8)
                if rgb.ndim == 2:
                    rgb = np.stack([rgb, rgb, rgb], axis=-1)
                elif rgb.shape[2] != 3:
                    rgb = rgb[:, :, :3].copy()
            mp_image = Image(ImageFormat.SRGB, np.ascontiguousarray(rgb))
            result = landmarker.detect(mp_image)
            return _TasksResultAdapter(result.face_landmarks)

    return _TasksFaceMeshWrapper()


def get_face_mesh():
    """
    Return a face mesh object that supports:
        res = mesh.process(rgb_numpy_array)  # RGB, HxWx3, uint8
        res.multi_face_landmarks  # list of faces
        res.multi_face_landmarks[0].landmark  # list of landmarks with .x, .y, .z

    Uses the legacy solutions API if available, otherwise the Tasks API (FaceLandmarker).
    """
    global _face_mesh_impl, _use_tasks_api
    if _face_mesh_impl is not None:
        return _face_mesh_impl
    if _has_solutions_api():
        _face_mesh_impl = _create_legacy_face_mesh()
        _use_tasks_api = False
    else:
        _face_mesh_impl = _create_tasks_face_mesh()
        _use_tasks_api = True
    return _face_mesh_impl
