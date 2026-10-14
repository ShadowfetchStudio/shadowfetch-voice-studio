import { beforeEach, describe, expect, it } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

async function renderApp() {
  delete (window as unknown as { __TAURI_INTERNALS__?: unknown }).__TAURI_INTERNALS__;
  const api = await import("@/lib/api");
  api.__resetForTests();
  const { useAppStore } = await import("@/store/appStore");
  const { __resetSpeakStore } = await import("@/features/speak/speakStore");
  const { __resetVoicesStore } = await import("@/store/voicesStore");
  __resetSpeakStore();
  __resetVoicesStore();
  useAppStore.setState({ page: "speak", params: {}, booted: false, bootError: null, settings: null, diagnostics: null, engines: [], models: [] });
  const { default: App } = await import("@/App");
  render(<App />);
}

describe("Studio workspace", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
    window.localStorage.clear();
  });

  it("reads a voice description, splits an audiobook, and checks VoiceStudio", async () => {
    const user = userEvent.setup();
    await renderApp();
    await screen.findByRole("textbox", { name: "Text to speak" }, { timeout: 4000 });
    const nav = screen.getByRole("navigation", { name: "Main" });
    await user.click(within(nav).getByRole("button", { name: "Studio" }));

    expect(await screen.findByRole("heading", { name: "Studio" })).toBeInTheDocument();
    expect(screen.getByLabelText("Describe the voice")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Read description" }));
    expect(await screen.findByText(/female, warm, british/)).toBeInTheDocument();
    expect(screen.getByText(/Not used: raspy/)).toBeInTheDocument();

    await user.click(screen.getByRole("tab", { name: "Audiobook" }));
    await user.click(screen.getByRole("button", { name: "Split into chapters" }));
    expect(await screen.findByRole("heading", { name: "Chapter 1" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Chapter 2" })).toBeInTheDocument();
    expect(screen.getByText("The road was empty.")).toBeInTheDocument();
    await user.click(screen.getAllByRole("button", { name: "Open in Speak" })[0]!);
    await waitFor(() => expect(screen.getByRole("textbox", { name: "Text to speak" })).toHaveValue("The road was empty."));

    await user.click(within(screen.getByRole("navigation", { name: "Main" })).getByRole("button", { name: "Studio" }));
    await user.click(screen.getByRole("tab", { name: "VoiceStudio" }));
    await user.click(screen.getByRole("button", { name: "Check VoiceStudio" }));
    expect(await screen.findByText(/not running/i)).toBeInTheDocument();
  });
});
