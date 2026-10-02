import os
import pytest

@pytest.fixture
def isolated_cache(tmp_path, monkeypatch):
    """
    Creates isolated directories for all queues inside tmp_path,
    and sets APP_CACHE_DIR and APP_RAW_DIR env variables.
    """
    # Create the cache queues
    for queue in [
        "01_pending_triage",
        "02_pending_expert",
        "02b_pending_testing",
        "03_pending_final",
        "04_pending_publish",
        "99_completed",
        "99_rejected"
    ]:
        (tmp_path / queue).mkdir(parents=True, exist_ok=True)
    
    # Create raw_transcripts
    raw_dir = tmp_path / "raw_transcripts"
    raw_dir.mkdir(exist_ok=True)
    
    # Set environment variables so the scripts use these paths
    monkeypatch.setenv("APP_CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("APP_RAW_DIR", str(raw_dir))
    
    return tmp_path
