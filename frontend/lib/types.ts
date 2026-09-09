/**
 * API types matching the backend Pydantic schemas.
 */

export interface UserPreferences {
  output_type: "instrumental" | "song";
  style?: string;
  mood?: string;
  energy?: "soft" | "medium" | "high";
  movement_feel?: string;
  custom_instruction?: string;
}

export interface UploadResponse {
  gcs_uri: string;
  preview_signed_url: string;
  filename: string;
  size_bytes: number;
}

export interface ChoreographySummary {
  moment_count: number;
  moment_labels: string[];
  duration_seconds: number;
  overall_energy: string;
  movement_tempo_bpm: number | null;
  analysis_confidence: "high" | "medium" | "low";
  low_confidence_warning: boolean;
}

export interface RunAgentResponse {
  final_video_signed_url: string;
  choreography_summary: ChoreographySummary;
  music_prompt: string;
  choreography_json: Record<string, unknown>;
}

export interface RunAgentRequest {
  gcs_uri: string;
  user_preferences: UserPreferences;
  cached_choreography?: Record<string, unknown>;
  cached_music_prompt?: string;
}

export interface ApiError {
  error: string;
}

export type PipelineStep =
  | "idle"
  | "uploading"
  | "analyzing"
  | "composing"
  | "generating"
  | "combining"
  | "done"
  | "error";
