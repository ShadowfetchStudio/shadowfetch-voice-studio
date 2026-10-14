import { useEffect, useState, type ReactNode } from "react";
import { AudioLines, BookOpen, Captions, Clapperboard, Mic, PenLine, Radio } from "lucide-react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { Textarea } from "@/components/ui/Field";
import { Tabs } from "@/components/ui/Tabs";
import { handleError, useAppStore } from "@/store/appStore";
import { useSpeakStore } from "@/features/speak/speakStore";
import type { SettingsPatch } from "@/lib/protocol";
import type { StudioCatalog, StudioChapter, StudioDesign, StudioDubCue, StudioVoiceStudioStatus } from "@/lib/studioProtocol";

type StudioTab = "design" | "dub" | "dictate" | "transcribe" | "audiobook" | "engine";

const TABS: Array<{ key: StudioTab; label: string; icon: ReactNode }> = [
  { key: "design", label: "Design", icon: <PenLine /> },
  { key: "dub", label: "Dub", icon: <Clapperboard /> },
  { key: "dictate", label: "Dictate", icon: <Mic /> },
  { key: "transcribe", label: "Transcribe", icon: <Captions /> },
  { key: "audiobook", label: "Audiobook", icon: <BookOpen /> },
  { key: "engine", label: "VoiceStudio", icon: <Radio /> },
];

/** Merged workspace: Shadowfetch's local studio plus VoiceStudio's design, dub, dictation, and audiobook jobs. */
export default function StudioPage() {
  const navigate = useAppStore((s) => s.navigate);
  const [tab, setTab] = useState<StudioTab>("design");
  const [catalog, setCatalog] = useState<StudioCatalog | null>(null);

  useEffect(() => {
    const req = api.studio.catalog();
    void req.then(setCatalog).catch((err) => handleError(err, "Couldn't open Studio"));
    return () => {
      void req.cancel();
    };
  }, []);

  return (
    <div className="flex flex-col gap-5">
      <header className="flex flex-col gap-1">
        <h1 className="text-[22px] font-semibold tracking-tight">Studio</h1>
        <p className="text-sm text-muted max-w-[68ch]">
          One app for cloning a voice and for the longer jobs: design a voice from a description, dub a recording,
          dictate, transcribe, or split an audiobook. Speech still runs on this computer. VoiceStudio, when you start it,
          adds its own engines beside Qwen3-TTS.
        </p>
        {catalog && (
          <p className="text-[12.5px] text-muted">
            {catalog.app} {catalog.version}
            {catalog.voicestudio.bundled ? " · VoiceStudio source is in this checkout" : " · VoiceStudio source is not checked out yet"}
          </p>
        )}
      </header>
      <Tabs items={TABS} value={tab} onChange={setTab} variant="pills" idPrefix="studio" />
      {tab === "design" && <DesignPanel />}
      {tab === "dub" && <DubPanel onSpeak={navigate} />}
      {tab === "dictate" && <DictatePanel onSpeak={navigate} />}
      {tab === "transcribe" && <TranscribePanel onSpeak={navigate} />}
      {tab === "audiobook" && <AudiobookPanel onSpeak={navigate} />}
      {tab === "engine" && <EnginePanel initialUrl={catalog?.voicestudio_url} />}
    </div>
  );
}

function openInSpeak(text: string, navigate: (page: "speak") => void) {
  useSpeakStore.getState().setText(text);
  navigate("speak");
}

function DesignPanel() {
  const [description, setDescription] = useState("a warm elderly British woman, slightly raspy");
  const [line, setLine] = useState("Hello. This is a short sample of the voice you described.");
  const [design, setDesign] = useState<StudioDesign | null>(null);
  const [busy, setBusy] = useState<"design" | "speak" | null>(null);
  const [audio, setAudio] = useState<string | null>(null);

  const parse = async () => {
    setBusy("design");
    try {
      setDesign(await api.studio.design(description));
    } catch (err) {
      handleError(err, "Couldn't read that description");
    } finally {
      setBusy(null);
    }
  };

  const speak = async () => {
    setBusy("speak");
    setAudio(null);
    try {
      const result = await api.studio.voiceStudioSpeak({ text: line, instruct: design?.instruct || undefined });
      setAudio(result.path.startsWith("data:") || result.path.startsWith("http") ? result.path : await api.shell.mediaSrc(result.path));
    } catch (err) {
      handleError(err, "VoiceStudio didn't speak");
    } finally {
      setBusy(null);
    }
  };

  return (
    <section aria-labelledby="studio-tab-design" className="flex flex-col gap-4 max-w-[760px]">
      <Textarea label="Describe the voice" value={description} onChange={(e) => setDescription(e.target.value)} rows={3} hint="Plain words. Shadowfetch maps them locally. Anything it doesn't recognise is listed, not dropped silently." />
      <div className="flex gap-2 flex-wrap">
        <Button variant="primary" onClick={() => void parse()} loading={busy === "design"}>Read description</Button>
      </div>
      {design && (
        <div className="panel p-4 flex flex-col gap-3">
          <p className="text-sm">
            Design notes: <span className="font-medium">{design.instruct || "nothing matched yet"}</span>
          </p>
          <ul className="text-[13px] text-muted grid sm:grid-cols-2 gap-1">
            {Object.entries(design.attrs).map(([key, value]) => (
              <li key={key}>{key}: {value}</li>
            ))}
          </ul>
          {design.unmatched.length > 0 && (
            <p className="text-[13px] text-muted">Not used: {design.unmatched.join(", ")}</p>
          )}
          <Textarea label="Sample line" value={line} onChange={(e) => setLine(e.target.value)} rows={2} />
          <Button variant="secondary" icon={<AudioLines />} onClick={() => void speak()} loading={busy === "speak"}>
            Speak with VoiceStudio
          </Button>
          {audio && <audio controls src={audio} className="w-full" />}
        </div>
      )}
    </section>
  );
}

function DubPanel({ onSpeak }: { onSpeak: (page: "speak") => void }) {
  const [cues, setCues] = useState<StudioDubCue[]>([]);
  const [note, setNote] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = async () => {
    setBusy(true);
    try {
      const [path] = await api.shell.pickAudioFiles();
      if (!path) return;
      const transcript = await api.transcribe.run({ path });
      const segments = transcript.segments.length
        ? transcript.segments
        : [{ text: transcript.text }];
      const sheet = await api.studio.dubCues(segments);
      setCues(sheet.cues);
      setNote(transcript.text);
    } catch (err) {
      handleError(err, "Couldn't build a dub");
    } finally {
      setBusy(false);
    }
  };

  return (
    <section aria-labelledby="studio-tab-dub" className="flex flex-col gap-4">
      <p className="text-sm text-muted max-w-[68ch]">
        Pick a recording. Local Whisper writes the lines, with timing when the model provides it. Edit the words, then
        open them in Speak to generate with a cloned voice.
      </p>
      <Button variant="primary" onClick={() => void load()} loading={busy}>Choose a recording</Button>
      {note && <p className="text-[13px] text-muted">{note}</p>}
      <ol className="flex flex-col gap-3">
        {cues.map((cue, index) => (
          <li key={cue.index} className="panel p-3 flex flex-col gap-2">
            <span className="text-[12px] text-muted">
              {cue.start_s == null ? "No timing" : `${cue.start_s.toFixed(2)}–${(cue.end_s ?? cue.start_s).toFixed(2)} s`}
              {cue.gap_after_s != null ? ` · ${cue.gap_after_s.toFixed(2)} s gap` : ""}
            </span>
            <Textarea label={`Line ${index + 1}`} value={cue.text} onChange={(e) => {
              const next = cues.slice();
              next[index] = { ...cue, text: e.target.value };
              setCues(next);
            }} rows={2} />
          </li>
        ))}
      </ol>
      {cues.length > 0 && (
        <Button variant="secondary" onClick={() => openInSpeak(cues.map((c) => c.text.trim()).filter(Boolean).join("\n\n"), onSpeak)}>
          Open script in Speak
        </Button>
      )}
    </section>
  );
}

function DictatePanel({ onSpeak }: { onSpeak: (page: "speak") => void }) {
  const [session, setSession] = useState<string | null>(null);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);

  const toggle = async () => {
    setBusy(true);
    try {
      if (!session) {
        const started = await api.record.start({});
        setSession(started.session_id);
      } else {
        const stopped = await api.record.stop(session);
        setSession(null);
        const extra = stopped as { working_path?: string | null };
        const path = extra.working_path || stopped.path;
        const transcript = await api.transcribe.run({ path });
        setText(transcript.text);
      }
    } catch (err) {
      handleError(err, "Dictation didn't finish");
      setSession(null);
    } finally {
      setBusy(false);
    }
  };

  return (
    <section aria-labelledby="studio-tab-dictate" className="flex flex-col gap-4 max-w-[760px]">
      <p className="text-sm text-muted">Record on this computer, then transcribe with local Whisper. Nothing is uploaded.</p>
      <Button variant={session ? "danger" : "primary"} onClick={() => void toggle()} loading={busy}>
        {session ? "Stop and transcribe" : "Start dictation"}
      </Button>
      <Textarea label="Transcript" value={text} onChange={(e) => setText(e.target.value)} rows={6} />
      {text.trim() && (
        <Button variant="secondary" onClick={() => openInSpeak(text.trim(), onSpeak)}>Speak this</Button>
      )}
    </section>
  );
}

function TranscribePanel({ onSpeak }: { onSpeak: (page: "speak") => void }) {
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);

  const run = async () => {
    setBusy(true);
    try {
      const [path] = await api.shell.pickAudioFiles();
      if (!path) return;
      const transcript = await api.transcribe.run({ path });
      setText(transcript.text);
    } catch (err) {
      handleError(err, "Couldn't transcribe that file");
    } finally {
      setBusy(false);
    }
  };

  return (
    <section aria-labelledby="studio-tab-transcribe" className="flex flex-col gap-4 max-w-[760px]">
      <Button variant="primary" onClick={() => void run()} loading={busy}>Choose audio to transcribe</Button>
      <Textarea label="Transcript" value={text} onChange={(e) => setText(e.target.value)} rows={8} />
      {text.trim() && <Button variant="secondary" onClick={() => openInSpeak(text.trim(), onSpeak)}>Open in Speak</Button>}
    </section>
  );
}

function AudiobookPanel({ onSpeak }: { onSpeak: (page: "speak") => void }) {
  const [text, setText] = useState("Chapter 1\n\nThe road was empty.\n\nChapter 2\n\nBy morning it was not.");
  const [chapters, setChapters] = useState<StudioChapter[]>([]);
  const [busy, setBusy] = useState(false);

  const split = async () => {
    setBusy(true);
    try {
      const result = await api.studio.chapters({ text });
      setChapters(result.chapters);
    } catch (err) {
      handleError(err, "Couldn't split that script");
    } finally {
      setBusy(false);
    }
  };

  const fromFile = async () => {
    const path = await api.shell.pickTextFile();
    if (!path) return;
    try {
      setText(await api.shell.readTextFile(path));
    } catch (err) {
      handleError(err, "Couldn't read that file");
    }
  };

  return (
    <section aria-labelledby="studio-tab-audiobook" className="flex flex-col gap-4">
      <Textarea label="Script" value={text} onChange={(e) => setText(e.target.value)} rows={8} hint="Chapter or Part headings, or Markdown headings, start a new chapter." />
      <div className="flex gap-2 flex-wrap">
        <Button variant="primary" onClick={() => void split()} loading={busy}>Split into chapters</Button>
        <Button variant="secondary" onClick={() => void fromFile()}>Open a text file</Button>
      </div>
      <ul className="flex flex-col gap-3">
        {chapters.map((chapter) => (
          <li key={chapter.index} className="panel p-3 flex flex-col gap-2">
            <div className="flex items-center justify-between gap-3">
              <h2 className="text-[15px] font-medium">{chapter.title}</h2>
              <span className="text-[12px] text-muted">{chapter.chars} characters</span>
            </div>
            <p className="text-sm text-muted whitespace-pre-wrap">{chapter.text}</p>
            <Button size="sm" variant="secondary" onClick={() => openInSpeak(chapter.text, onSpeak)}>Open in Speak</Button>
          </li>
        ))}
      </ul>
    </section>
  );
}

function EnginePanel({ initialUrl }: { initialUrl?: string }) {
  const [url, setUrl] = useState(initialUrl || "http://127.0.0.1:3900");
  const [status, setStatus] = useState<StudioVoiceStudioStatus | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (initialUrl) setUrl(initialUrl);
  }, [initialUrl]);

  const check = async () => {
    setBusy(true);
    try {
      await api.system.settingsSet({ voicestudio_url: url } as SettingsPatch);
      setStatus(await api.studio.voiceStudioStatus(url));
    } catch (err) {
      handleError(err, "Couldn't reach VoiceStudio");
    } finally {
      setBusy(false);
    }
  };

  return (
    <section aria-labelledby="studio-tab-engine" className="flex flex-col gap-4 max-w-[760px]">
      <p className="text-sm text-muted">
        VoiceStudio stays its own program, under the AGPL-3.0. Shadowfetch talks to it on this computer at the address
        below. Clone it with <code>scripts/fetch-voicestudio.sh</code>, then start the API with <code>scripts/run-voicestudio-api.sh</code>.
      </p>
      <label className="flex flex-col gap-1.5 text-[13px] font-medium">
        VoiceStudio address
        <input className="field-input" value={url} onChange={(e) => setUrl(e.target.value)} spellCheck={false} />
      </label>
      <Button variant="primary" onClick={() => void check()} loading={busy}>Check VoiceStudio</Button>
      {status && (
        <div className="panel p-4 text-sm flex flex-col gap-1">
          <p>{status.message}</p>
          <p className="text-muted">{status.url} · {status.status}{status.version ? ` · ${status.version}` : ""}</p>
          {status.bundle.root && <p className="text-muted">Source: {status.bundle.root}</p>}
        </div>
      )}
    </section>
  );
}
