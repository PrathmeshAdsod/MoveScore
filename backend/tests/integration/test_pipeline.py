"""
Integration test for the full pipeline using mocked services.

Tests that the ADK agent correctly orchestrates the pipeline,
handles Generate Again caching, and propagates specific errors at every stage.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

# Make backend/ importable
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from utils.errors import (
    ChoreographyAnalysisError,
    InvalidVideoDurationError,
    MediaCombineError,
    MusicGenerationError,
    MusicPlanError,
)


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
    return "15-second Afrobeat instrumental. High energy. Strong hit at 0:03. Freeze at 0:10."


class TestAgentWorkflow:
    def test_full_run_calls_all_tools_and_combine(
        self, mock_choreography_dict, mock_music_prompt
    ) -> None:
        from agent.workflow import ChoreographyMusicAgent
        from schemas.api import UserPreferences

        prefs = UserPreferences(style="Afrobeat", mood="Euphoric", energy="high")

        with (
            patch(
                "agent.workflow.analyze_choreography_tool",
                return_value=json.dumps(mock_choreography_dict),
            ) as mock_an,
            patch("agent.workflow.plan_music_tool", return_value=mock_music_prompt) as mock_pl,
            patch(
                "agent.workflow.generate_music_tool", return_value="gs://bucket/audio/test.mp3"
            ) as mock_gen,
            patch(
                "agent.workflow.combine_from_gcs", return_value="https://signed.url/final.mp4"
            ) as mock_comb,
        ):
            agent = ChoreographyMusicAgent()
            result = agent.run(
                video_bytes=b"fake_video",
                video_mime_type="video/mp4",
                video_gcs_uri="gs://bucket/uploads/test.mp4",
                user_preferences=prefs,
            )

            assert mock_an.called
            assert mock_pl.called
            assert mock_gen.called
            assert mock_comb.called
            assert result.final_video_signed_url == "https://signed.url/final.mp4"
            assert result.music_prompt == mock_music_prompt
            assert result.choreography.duration_seconds == 15.0

    def test_generate_again_skips_analysis_with_cache(
        self, mock_choreography_dict, mock_music_prompt
    ) -> None:
        from agent.workflow import ChoreographyMusicAgent
        from schemas.api import UserPreferences

        prefs = UserPreferences(style="House")

        with (
            patch("agent.workflow.analyze_choreography_tool") as mock_an,
            patch("agent.workflow.plan_music_tool", return_value=mock_music_prompt) as mock_pl,
            patch(
                "agent.workflow.generate_music_tool", return_value="gs://bucket/audio/new.mp3"
            ) as mock_gen,
            patch("agent.workflow.combine_from_gcs", return_value="https://signed.url/final2.mp4"),
        ):
            agent = ChoreographyMusicAgent()
            result = agent.run(
                video_bytes=b"",
                video_mime_type="video/mp4",
                video_gcs_uri="gs://bucket/uploads/test.mp4",
                user_preferences=prefs,
                cached_choreography=mock_choreography_dict,
            )

            assert not mock_an.called  # skipped
            assert mock_pl.called
            assert mock_gen.called
            assert result.final_video_signed_url == "https://signed.url/final2.mp4"

    def test_generate_again_skips_both_when_fully_cached(
        self, mock_choreography_dict, mock_music_prompt
    ) -> None:
        from agent.workflow import ChoreographyMusicAgent
        from schemas.api import UserPreferences

        prefs = UserPreferences(energy="soft")

        with (
            patch("agent.workflow.analyze_choreography_tool") as mock_an,
            patch("agent.workflow.plan_music_tool") as mock_pl,
            patch(
                "agent.workflow.generate_music_tool", return_value="gs://bucket/audio/regen.mp3"
            ) as mock_gen,
            patch("agent.workflow.combine_from_gcs", return_value="https://signed.url/regen.mp4"),
        ):
            agent = ChoreographyMusicAgent()
            result = agent.run(
                video_bytes=b"",
                video_mime_type="video/mp4",
                video_gcs_uri="gs://bucket/uploads/test.mp4",
                user_preferences=prefs,
                cached_choreography=mock_choreography_dict,
                cached_music_prompt=mock_music_prompt,
            )

            assert not mock_an.called  # skipped
            assert not mock_pl.called  # skipped
            assert mock_gen.called
            assert result.final_video_signed_url == "https://signed.url/regen.mp4"

    # ── Error Propagation Tests at Each Stage ──
    def test_stage1_analysis_failure_propagates(self) -> None:
        from agent.workflow import ChoreographyMusicAgent
        from schemas.api import UserPreferences

        prefs = UserPreferences()
        with patch(
            "agent.workflow.analyze_choreography_tool",
            side_effect=ChoreographyAnalysisError("Gemini quota exhausted"),
        ):
            agent = ChoreographyMusicAgent()
            with pytest.raises(ChoreographyAnalysisError) as exc_info:
                agent.run(
                    video_bytes=b"video",
                    video_mime_type="video/mp4",
                    video_gcs_uri="gs://bucket/uploads/test.mp4",
                    user_preferences=prefs,
                )
            assert "Gemini quota exhausted" in str(exc_info.value)

    def test_stage2_planning_failure_propagates(self, mock_choreography_dict) -> None:
        from agent.workflow import ChoreographyMusicAgent
        from schemas.api import UserPreferences

        prefs = UserPreferences()
        with (
            patch(
                "agent.workflow.analyze_choreography_tool",
                return_value=json.dumps(mock_choreography_dict),
            ),
            patch(
                "agent.workflow.plan_music_tool",
                side_effect=MusicPlanError("Gemini reasoning failed"),
            ),
        ):
            agent = ChoreographyMusicAgent()
            with pytest.raises(MusicPlanError) as exc_info:
                agent.run(
                    video_bytes=b"video",
                    video_mime_type="video/mp4",
                    video_gcs_uri="gs://bucket/uploads/test.mp4",
                    user_preferences=prefs,
                )
            assert "Gemini reasoning failed" in str(exc_info.value)

    def test_stage3_music_generation_failure_propagates(
        self, mock_choreography_dict, mock_music_prompt
    ) -> None:
        from agent.workflow import ChoreographyMusicAgent
        from schemas.api import UserPreferences

        prefs = UserPreferences()
        with (
            patch(
                "agent.workflow.analyze_choreography_tool",
                return_value=json.dumps(mock_choreography_dict),
            ),
            patch("agent.workflow.plan_music_tool", return_value=mock_music_prompt),
            patch(
                "agent.workflow.generate_music_tool",
                side_effect=MusicGenerationError("Lyria 3.5 permission denied"),
            ),
        ):
            agent = ChoreographyMusicAgent()
            with pytest.raises(MusicGenerationError) as exc_info:
                agent.run(
                    video_bytes=b"video",
                    video_mime_type="video/mp4",
                    video_gcs_uri="gs://bucket/uploads/test.mp4",
                    user_preferences=prefs,
                )
            assert "Lyria 3.5 permission denied" in str(exc_info.value)

    def test_stage4_combine_failure_propagates(
        self, mock_choreography_dict, mock_music_prompt
    ) -> None:
        from agent.workflow import ChoreographyMusicAgent
        from schemas.api import UserPreferences

        prefs = UserPreferences()
        with (
            patch(
                "agent.workflow.analyze_choreography_tool",
                return_value=json.dumps(mock_choreography_dict),
            ),
            patch("agent.workflow.plan_music_tool", return_value=mock_music_prompt),
            patch("agent.workflow.generate_music_tool", return_value="gs://bucket/audio/test.mp3"),
            patch(
                "agent.workflow.combine_from_gcs",
                side_effect=MediaCombineError("FFmpeg transcode error"),
            ),
        ):
            agent = ChoreographyMusicAgent()
            with pytest.raises(MediaCombineError) as exc_info:
                agent.run(
                    video_bytes=b"video",
                    video_mime_type="video/mp4",
                    video_gcs_uri="gs://bucket/uploads/test.mp4",
                    user_preferences=prefs,
                )
            assert "FFmpeg transcode error" in str(exc_info.value)


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
        assert "MoveScore" in resp.json()["service"]

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

    def test_upload_duration_over_60s_returns_400(self, client) -> None:
        with patch(
            "services.ffmpeg_service.validate_video_duration",
            side_effect=InvalidVideoDurationError(duration_sec=75.0, max_sec=60.0),
        ):
            resp = client.post(
                "/upload",
                files={"file": ("video.mp4", b"fake_long_video", "video/mp4")},
            )
            assert resp.status_code == 400
            assert "75.0s" in resp.json()["detail"]
            assert "Maximum supported duration is 60 seconds" in resp.json()["detail"]

    def test_upload_success_within_60s(self, client) -> None:
        with (
            patch("services.ffmpeg_service.validate_video_duration", return_value=15.0),
            patch("services.storage.upload_bytes", return_value="gs://bucket/uploads/test.mp4"),
            patch(
                "services.storage.generate_signed_url",
                return_value="https://signed.url/preview.mp4",
            ),
        ):
            resp = client.post(
                "/upload",
                files={"file": ("video.mp4", b"fake_short_video", "video/mp4")},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["gcs_uri"] == "gs://bucket/uploads/test.mp4"
            assert data["preview_signed_url"] == "https://signed.url/preview.mp4"

    def test_run_agent_requires_gcs_uri(self, client) -> None:
        resp = client.post("/run-agent", json={})
        assert resp.status_code == 422

    def test_run_agent_with_mocks(self, client, mock_choreography_dict, mock_music_prompt) -> None:
        from schemas.choreography import ChoreographySchema

        choreography = ChoreographySchema.model_validate(mock_choreography_dict)

        with patch("routes.run_agent._agent.run") as mock_run:
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
