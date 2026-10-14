import { requestRaw, type RequestOptions } from "./api";
import type {
  StudioCatalog,
  StudioChapterParams,
  StudioChapters,
  StudioDesign,
  StudioDubCues,
  StudioDubSegment,
  StudioScript,
  StudioScriptCue,
  StudioVoiceStudioSpeak,
  StudioVoiceStudioSpeakParams,
  StudioVoiceStudioStatus,
} from "./studioProtocol";

type Opts = RequestOptions | undefined;

/** Typed Studio calls. Uses the untyped request path so the rest of the protocol table can stay as it is. */
export const studioApi = {
  catalog: (o?: Opts) => requestRaw<StudioCatalog>("studio.catalog", {}, o),
  design: (description: string, o?: Opts) => requestRaw<StudioDesign>("studio.design", { description }, o),
  chapters: (p: StudioChapterParams, o?: Opts) => requestRaw<StudioChapters>("studio.chapters", p, o),
  dubCues: (segments: StudioDubSegment[], o?: Opts) => requestRaw<StudioDubCues>("studio.dub_cues", { segments }, o),
  script: (cues: StudioScriptCue[], o?: Opts) => requestRaw<StudioScript>("studio.script", { cues }, o),
  voiceStudioStatus: (url?: string, o?: Opts) => requestRaw<StudioVoiceStudioStatus>("studio.voicestudio.status", url ? { url } : {}, o),
  voiceStudioSpeak: (p: StudioVoiceStudioSpeakParams, o?: Opts) => requestRaw<StudioVoiceStudioSpeak>("studio.voicestudio.speak", p, o),
};
