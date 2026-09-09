/**
 * Frontend API client for the Agentic Cinema backend.
 * All requests go to NEXT_PUBLIC_BACKEND_URL.
 */

import type {
  RunAgentRequest,
  RunAgentResponse,
  UploadResponse,
} from "./types";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8080";

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let message = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      message = body?.error ?? body?.detail ?? message;
    } catch {
      // ignore parse error
    }
    throw new Error(message);
  }
  return res.json() as Promise<T>;
}

export async function uploadVideo(file: File): Promise<UploadResponse> {
  const form = new FormData();
  form.append("file", file);

  const res = await fetch(`${BACKEND_URL}/upload`, {
    method: "POST",
    body: form,
  });

  return handleResponse<UploadResponse>(res);
}

export async function runAgent(
  request: RunAgentRequest
): Promise<RunAgentResponse> {
  const res = await fetch(`${BACKEND_URL}/run-agent`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });

  return handleResponse<RunAgentResponse>(res);
}

export async function checkHealth(): Promise<{ status: string }> {
  const res = await fetch(`${BACKEND_URL}/health`);
  return handleResponse<{ status: string }>(res);
}
