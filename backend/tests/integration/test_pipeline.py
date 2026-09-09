"""
Integration test for the full pipeline using mocked services.

Tests that the ADK agent correctly orchestrates all four tools
and that the FastAPI routes respond correctly.

No real API calls are made — all external services are mocked.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# Make backend/ importable
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


@pytest.fixture
def mock_choreography_dict():
    return {
        "duration_seconds": 15.0,
        "overall_energy": "high",
        "movement_tempo_bpm": 110,
        "segments": [
            {
                "start_sec": 0.0,
                "end_sec": 15.0,
                "label": "routine",
                "description": "full dance",
                "energy": "high",
                "move_type": "sequence",
                "intensity": 7,
            }
        ],
        "key_moments": [
            {"time_sec": 3.0, "type": "accent", "note": "hit"},
            {"time_sec": 10.0, "type": "freeze", "note": "stop"},
            {"time_sec": 15.0, "type": "final_pose", "note": "pose"},
        ],
        "movement_patterns": {
            "repeated_motifs": [],
            "dominant_style": "hip-hop",
            "has_buildup": False,
            "has_drop": True,
            "has_freeze": True,
            "has_final_pose": True,
        },
        "analysis_confidence": "high",
        "analysis_notes": "Good quality.",
    }


@pytest.fixture
def mock_music_prompt():
    return "18-second Afrobeat instrumental. High energy. Strong hit at 0:03. Freeze at 0:10."


class TestAgentWorkflow:
    def test_full_run_calls_all_four_tools(
        self, mock_choreography_dict, mock_music_prompt
    ) -> None:
        from schemas.choreography import ChoreographySchema
        from schemas.api import UserPreferences
        from agent.workflow import ChoreographyMusicAgent

        choreography = ChoreographySchema.model_validate(mock_choreography_dict)
        prefs = UserPreferences(style="Afrobeat", mood="Euphoric", energy="high")

        with (
            patch("agent.tools.analyze_choreography.analyze_choreography_tool", return_value=choreography) as mock_t1,
            patch("agent.tools.plan_music.plan_music_tool", return_value=mock_music_prompt) as mock_t2,
            patch("agent.tools.generate_music.generate_music_tool", return_value="gs://bucket/audio/test.mp3") as mock_t3,
            patch("agent.tools.combine_media.combine_media_tool", return_value="https://signed.url/final.mp4") as mock_t4,
            patch("agent.workflow.analyze_choreography_tool", return_value=choreography),
            patch("agent.workflow.plan_music_tool", return_value=mock_music_prompt),
            patch("agent.workflow.generate_music_tool", return_value="gs://bucket/audio/test.mp3"),
            patch("agent.workflow.combine_media_tool", return_value="https://signed.url/final.mp4"),
        ):
            agent = ChoreographyMusicAgent()
            result = agent.run(
                video_bytes=b"fake_video",
                video_mime_type="video/mp4",
                video_gcs_uri="gs://bucket/uploads/test.mp4",
                user_preferences=prefs,
            )

        assert result.final_video_signed_url == "https://signed.url/final.mp4"
        assert result.music_prompt == mock_music_prompt
        assert result.choreography.duration_seconds == 15.0

    def test_generate_again_skips_analysis_with_cache(
        self, mock_choreography_dict, mock_music_prompt
    ) -> None:
        from schemas.choreography import ChoreographySchema
        from schemas.api import UserPreferences
        from agent.workflow import ChoreographyMusicAgent

        prefs = UserPreferences(style="House")

        with (
            patch("agent.workflow.analyze_choreography_tool") as mock_t1,
            patch("agent.workflow.plan_music_tool", return_value="new music prompt") as mock_t2,
            patch("agent.workflow.generate_music_tool", return_value="gs://bucket/audio/new.mp3") as mock_t3,
            patch("agent.workflow.combine_media_tool", return_value="https://signed.url/final2.mp4") as mock_t4,
        ):
            agent = ChoreographyMusicAgent()
            result = agent.run(
                video_bytes=b"",
                video_mime_type="video/mp4",
                video_gcs_uri="gs://bucket/uploads/test.mp4",
                user_preferences=prefs,
                cached_choreography=mock_choreography_dict,  # cached!
            )

        # Tool 1 must NOT be called when cache is provided
        mock_t1.assert_not_called()
        # Tool 2 must be called (preferences changed)
        mock_t2.assert_called_once()
        assert result.final_video_signed_url == "https://signed.url/final2.mp4"

    def test_generate_again_skips_both_when_fully_cached(
        self, mock_choreography_dict, mock_music_prompt
    ) -> None:
        from schemas.api import UserPreferences
        from agent.workflow import ChoreographyMusicAgent

        prefs = UserPreferences(energy="soft")

        with (
            patch("agent.workflow.analyze_choreography_tool") as mock_t1,
            patch("agent.workflow.plan_music_tool") as mock_t2,
            patch("agent.workflow.generate_music_tool", return_value="gs://bucket/audio/regen.mp3"),
            patch("agent.workflow.combine_media_tool", return_value="https://signed.url/regen.mp4"),
        ):
            agent = ChoreographyMusicAgent()
            result = agent.run(
                video_bytes=b"",
                video_mime_type="video/mp4",
                video_gcs_uri="gs://bucket/uploads/test.mp4",
                user_preferences=prefs,
                cached_choreography=mock_choreography_dict,
                cached_music_prompt=mock_music_prompt,  # also cached!
            )

        mock_t1.assert_not_called()
        mock_t2.assert_not_called()
        assert result.final_video_signed_url == "https://signed.url/regen.mp4"


class TestApiRoutes:
    @pytest.fixture
    def client(self):
        from main import app
        return TestClient(app)

    def test_health_endpoint(self, client) -> None:
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_root_endpoint(self, client) -> None:
        resp = client.get("/")
        assert resp.status_code == 200
        assert "Agentic Cinema" in resp.json()["service"]

    def test_upload_no_file_returns_422(self, client) -> None:
        resp = client.post("/upload")
        assert resp.status_code == 422

    def test_upload_wrong_type_returns_415(self, client) -> None:
        resp = client.post(
            "/upload",
            files={"file": ("test.pdf", b"fake pdf content", "application/pdf")},
        )
        assert resp.status_code == 415

    def test_upload_empty_file_returns_400(self, client) -> None:
        resp = client.post(
            "/upload",
            files={"file": ("video.mp4", b"", "video/mp4")},
        )
        assert resp.status_code == 400

    def test_run_agent_requires_gcs_uri(self, client) -> None:
        resp = client.post("/run-agent", json={})
        assert resp.status_code == 422

    def test_run_agent_with_mocks(
        self, client, mock_choreography_dict, mock_music_prompt
    ) -> None:
        from schemas.choreography import ChoreographySchema

        choreography = ChoreographySchema.model_validate(mock_choreography_dict)

        with (
            patch("routes.run_agent._agent.run") as mock_run,
        ):
            from agent.workflow import AgentResult

            mock_run.return_value = AgentResult(
                choreography=choreography,
                music_prompt=mock_music_prompt,
                audio_gcs_uri="gs://bucket/audio/test.mp3",
                final_video_signed_url="https://signed.url/final.mp4",
            )

            resp = client.post(
                "/run-agent",
                json={
                    "gcs_uri": "gs://bucket/uploads/test.mp4",
                    "user_preferences": {
                        "output_type": "instrumental",
                        "style": "Afrobeat",
                        "mood": "Euphoric",
                        "energy": "high",
                    },
                    "cached_choreography": mock_choreography_dict,
                },
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["final_video_signed_url"] == "https://signed.url/final.mp4"
        assert "choreography_summary" in data
        assert data["choreography_summary"]["moment_count"] == 3
