/** Studio workspace types for the merged VoiceStudio jobs.
 *
 * These live beside the worker protocol so the Studio page and the typed client
 * can compile without rewriting the rest of the protocol mirror.
 */

export interface StudioWorkspace {
  id: "speak" | "design" | "dub" | "dictate" | "transcribe" | "audiobook" | string;
  title: string;
  summary: string;
  engine: "shadowfetch" | "voicestudio" | "both" | string;
}

export interface StudioBundle {
  bundled: boolean;
  root: string | null;
  default_url: string;
  license: string;
  upstream: string;
}

export interface StudioCatalog {
  app: string;
  version: string;
  workspaces: StudioWorkspace[];
  voicestudio_url: string;
  voicestudio: StudioBundle;
}

export interface StudioDesign {
  description: string;
  attrs: Record<string, string>;
  instruct: string;
  matched: Array<{ category: string; token: string; phrase: string }>;
  unmatched: string[];
}

export interface StudioChapter {
  index: number;
  title: string;
  text: string;
  chars: number;
}

export interface StudioChapterParams {
  text: string;
  max_chars?: number;
}

export interface StudioChapters {
  chapters: StudioChapter[];
  count: number;
}

export interface StudioDubCue {
  index: number;
  start_s: number | null;
  end_s: number | null;
  duration_s: number | null;
  text: string;
  gap_after_s: number | null;
}

export interface StudioDubSegment {
  start?: number;
  end?: number;
  text?: string;
}

export interface StudioDubCues {
  cues: StudioDubCue[];
  count: number;
  script: string;
}

export interface StudioScriptCue {
  text?: string;
}

export interface StudioScript {
  script: string;
  chars: number;
}

export interface StudioVoiceStudioStatus {
  url: string;
  reachable: boolean;
  starting: boolean;
  status: string;
  version?: string | null;
  device?: string | null;
  protocol?: string | null;
  message: string;
  bundle: StudioBundle;
}

export interface StudioVoiceStudioSpeakParams {
  text: string;
  url?: string;
  voice?: string;
  instruct?: string | null;
  model?: string;
}

export interface StudioVoiceStudioSpeak {
  path: string;
  bytes: number;
  content_type: string;
  url: string;
  elapsed_s?: number;
}
