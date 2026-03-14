"""Verify the project scaffold: package importable, dependencies available."""


def test_local_tts_package_importable():
    import local_tts

    assert local_tts is not None


def test_tts_subpackage_importable():
    import local_tts.tts

    assert local_tts.tts is not None


def test_fastapi_available():
    import fastapi

    assert fastapi is not None


def test_uvicorn_available():
    import uvicorn

    assert uvicorn is not None


def test_torch_available():
    import torch

    assert torch is not None


def test_transformers_available():
    import transformers

    assert transformers is not None


def test_huggingface_hub_available():
    import huggingface_hub

    assert huggingface_hub is not None
