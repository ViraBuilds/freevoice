const PREVIEW_SAMPLES = {
  "American English": "Hello! This is a preview of my voice in FreeVoice.",
  "British English": "Good day! Here is a quick preview of my voice in FreeVoice.",
  "Spanish": "Hola, esta es una vista previa de mi voz en FreeVoice.",
  "French": "Bonjour, ceci est un aperçu de ma voix dans FreeVoice.",
  "Hindi": "नमस्ते, यह फ्रीवॉइस में मेरी आवाज़ का पूर्वावलोकन है।",
  "Italian": "Ciao, questa è un'anteprima della mia voce su FreeVoice.",
  "Japanese": "こんにちは、これはFreeVoiceの音声プレビューです。",
  "Portuguese": "Olá, esta é uma prévia da minha voz no FreeVoice.",
  "Chinese": "你好，这是 FreeVoice 的语音预览。",
};

let allVoices = [];
let currentObjectUrl = null;

const els = {
  tabs: document.querySelectorAll(".tab"),
  panels: document.querySelectorAll(".panel"),
  text: document.getElementById("tts-text"),
  charCount: document.getElementById("char-count"),
  clearBtn: document.getElementById("clear-text-btn"),
  langFilter: document.getElementById("lang-filter"),
  voiceSelect: document.getElementById("voice-select"),
  voiceDesc: document.getElementById("voice-desc"),
  previewBtn: document.getElementById("preview-voice-btn"),
  speedRange: document.getElementById("speed-range"),
  speedVal: document.getElementById("speed-val"),
  formatSelect: document.getElementById("format-select"),
  generateBtn: document.getElementById("generate-btn"),
  downloadLink: document.getElementById("download-link"),
  player: document.getElementById("audio-player"),
  studioStatus: document.getElementById("studio-status"),
  cloneForm: document.getElementById("clone-form"),
  cloneSubmitBtn: document.getElementById("clone-submit-btn"),
  cloneStatus: document.getElementById("clone-status"),
  clonedList: document.getElementById("cloned-voices-list"),
  batchInput: document.getElementById("batch-input"),
  batchVoice: document.getElementById("batch-voice"),
  batchFormat: document.getElementById("batch-format"),
  batchRunBtn: document.getElementById("batch-run-btn"),
  batchStatus: document.getElementById("batch-status"),
  apiBaseUrl: document.getElementById("api-base-url"),
};

function setStatus(el, msg, type = "") {
  el.textContent = msg;
  el.className = `status ${type}`.trim();
}

function updateCharCount() {
  els.charCount.textContent = `${els.text.value.length.toLocaleString()} characters`;
}

function populateVoiceDropdowns() {
  const filter = els.langFilter.value;
  const filtered = allVoices.filter((v) => {
    if (filter === "all") return true;
    if (filter === "clone") return v.lang_code === "clone";
    return v.language === filter;
  });

  const previous = els.voiceSelect.value || "af_heart";
  els.voiceSelect.innerHTML = "";

  filtered.forEach((v) => {
    const opt = document.createElement("option");
    opt.value = v.id;
    opt.textContent = `${v.name} — ${v.language} (${v.gender}) [${v.id}]`;
    els.voiceSelect.appendChild(opt);
  });

  if (filtered.some((v) => v.id === previous)) {
    els.voiceSelect.value = previous;
  }
  updateVoiceDescription();

  // Populate batch default voice selector with all voices
  const prevBatch = els.batchVoice.value || "af_heart";
  els.batchVoice.innerHTML = "";
  allVoices.forEach((v) => {
    const opt = document.createElement("option");
    opt.value = v.id;
    opt.textContent = `${v.name} (${v.id})`;
    els.batchVoice.appendChild(opt);
  });
  if (allVoices.some((v) => v.id === prevBatch)) {
    els.batchVoice.value = prevBatch;
  }
}

function updateVoiceDescription() {
  const selected = allVoices.find((v) => v.id === els.voiceSelect.value);
  els.voiceDesc.textContent = selected ? `${selected.provider} · ${selected.description}` : "";
}

function renderClonedVoicesList() {
  const clones = allVoices.filter((v) => v.lang_code === "clone");
  els.clonedList.innerHTML = "";

  if (clones.length === 0) {
    els.clonedList.innerHTML = `<p class="hint">No cloned voices saved yet. Upload a 3-second clip on the left.</p>`;
    return;
  }

  clones.forEach((c) => {
    const row = document.createElement("div");
    row.className = "clone-item";

    const info = document.createElement("div");
    info.innerHTML = `
      <div class="clone-item-title">${c.name}</div>
      <div class="clone-item-sub">ID: <code>${c.id}</code> · ${c.language} · ${c.description}</div>
    `;

    const actions = document.createElement("div");
    actions.style.display = "flex";
    actions.style.gap = "0.4rem";

    const useBtn = document.createElement("button");
    useBtn.type = "button";
    useBtn.className = "btn-secondary";
    useBtn.style.padding = "0.35rem 0.65rem";
    useBtn.style.fontSize = "0.8rem";
    useBtn.textContent = "Use";
    useBtn.onclick = () => {
      els.langFilter.value = "all";
      populateVoiceDropdowns();
      els.voiceSelect.value = c.id;
      updateVoiceDescription();
      switchTab("studio");
    };

    const delBtn = document.createElement("button");
    delBtn.type = "button";
    delBtn.className = "btn-danger";
    delBtn.textContent = "Delete";
    delBtn.onclick = async () => {
      const slug = c.id.replace(/^clone:/, "");
      await fetch(`/v1/voices/clone/${encodeURIComponent(slug)}`, { method: "DELETE" });
      await loadVoices();
    };

    actions.append(useBtn, delBtn);
    row.append(info, actions);
    els.clonedList.appendChild(row);
  });
}

async function loadVoices() {
  try {
    const res = await fetch("/v1/voices");
    const data = await res.json();
    allVoices = data.voices || [];
    populateVoiceDropdowns();
    renderClonedVoicesList();
  } catch (err) {
    setStatus(els.studioStatus, `Failed to load voices: ${err.message}`, "err");
  }
}

async function synthesizeAudio({ text, voice, speed, format, statusEl, buttonEl }) {
  buttonEl.disabled = true;
  const started = performance.now();
  setStatus(statusEl, "Synthesizing audio (first run downloads model weights)...");

  try {
    const res = await fetch("/v1/audio/speech", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        model: voice.startsWith("clone:") ? "qwen3-tts-0.6b" : "kokoro-82m",
        input: text,
        voice,
        speed: parseFloat(speed),
        response_format: format,
      }),
    });

    if (!res.ok) {
      const errData = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(errData.detail || "Synthesis failed");
    }

    const blob = await res.blob();
    if (currentObjectUrl) {
      URL.revokeObjectURL(currentObjectUrl);
    }
    currentObjectUrl = URL.createObjectURL(blob);

    els.player.src = currentObjectUrl;
    await els.player.play().catch(() => {});

    els.downloadLink.href = currentObjectUrl;
    els.downloadLink.download = `freevoice_${voice.replace(":", "_")}.${format}`;
    els.downloadLink.classList.remove("disabled");

    const elapsed = ((performance.now() - started) / 1000).toFixed(2);
    setStatus(statusEl, `Ready in ${elapsed}s (${(blob.size / 1024).toFixed(1)} KB).`, "ok");
  } catch (err) {
    setStatus(statusEl, err.message, "err");
  } finally {
    buttonEl.disabled = false;
  }
}

function switchTab(tabName) {
  els.tabs.forEach((t) => t.classList.toggle("active", t.dataset.tab === tabName));
  els.panels.forEach((p) => p.classList.toggle("active", p.id === `tab-${tabName}`));
}

// Event bindings
els.tabs.forEach((tab) => {
  tab.addEventListener("click", () => switchTab(tab.dataset.tab));
});

els.text.addEventListener("input", updateCharCount);
els.clearBtn.addEventListener("click", () => {
  els.text.value = "";
  updateCharCount();
});

els.langFilter.addEventListener("change", populateVoiceDropdowns);
els.voiceSelect.addEventListener("change", updateVoiceDescription);

els.speedRange.addEventListener("input", () => {
  els.speedVal.textContent = `${parseFloat(els.speedRange.value).toFixed(2)}x`;
});

els.generateBtn.addEventListener("click", () => {
  const text = els.text.value.trim();
  if (!text) {
    setStatus(els.studioStatus, "Please enter text to synthesize.", "err");
    return;
  }
  synthesizeAudio({
    text,
    voice: els.voiceSelect.value,
    speed: els.speedRange.value,
    format: els.formatSelect.value,
    statusEl: els.studioStatus,
    buttonEl: els.generateBtn,
  });
});

els.previewBtn.addEventListener("click", () => {
  const selected = allVoices.find((v) => v.id === els.voiceSelect.value);
  const sampleText =
    (selected && PREVIEW_SAMPLES[selected.language]) ||
    "Hello! This is a preview of my voice in FreeVoice.";
  synthesizeAudio({
    text: sampleText,
    voice: els.voiceSelect.value,
    speed: 1.0,
    format: "mp3",
    statusEl: els.studioStatus,
    buttonEl: els.previewBtn,
  });
});

els.cloneForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const fileInput = document.getElementById("clone-file");
  if (!fileInput.files || fileInput.files.length === 0) {
    setStatus(els.cloneStatus, "Please choose an audio sample.", "err");
    return;
  }

  const formData = new FormData();
  formData.append("name", document.getElementById("clone-name").value);
  formData.append("language", document.getElementById("clone-lang").value);
  formData.append("ref_text", document.getElementById("clone-ref-text").value);
  formData.append("sample", fileInput.files[0]);

  els.cloneSubmitBtn.disabled = true;
  setStatus(els.cloneStatus, "Saving reference voice sample...");

  try {
    const res = await fetch("/v1/voices/clone", {
      method: "POST",
      body: formData,
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "Voice cloning setup failed");
    }
    setStatus(
      els.cloneStatus,
      `Saved "${data.name}" (${data.duration_seconds}s sample) as ${data.id}.`,
      "ok"
    );
    els.cloneForm.reset();
    await loadVoices();
  } catch (err) {
    setStatus(els.cloneStatus, err.message, "err");
  } finally {
    els.cloneSubmitBtn.disabled = false;
  }
});

els.batchRunBtn.addEventListener("click", async () => {
  const raw = els.batchInput.value.trim();
  if (!raw) {
    setStatus(els.batchStatus, "Enter at least one line or a JSON array.", "err");
    return;
  }

  let items = [];
  if (raw.startsWith("[")) {
    try {
      items = JSON.parse(raw);
    } catch (err) {
      setStatus(els.batchStatus, `Invalid JSON: ${err.message}`, "err");
      return;
    }
  } else {
    items = raw
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter(Boolean)
      .map((text) => ({ text }));
  }

  els.batchRunBtn.disabled = true;
  setStatus(els.batchStatus, `Generating ${items.length} audio files...`);

  try {
    const res = await fetch("/v1/audio/batch", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        items,
        default_voice: els.batchVoice.value,
        response_format: els.batchFormat.value,
      }),
    });

    if (!res.ok) {
      const errData = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(errData.detail || "Batch synthesis failed");
    }

    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "freevoice_batch.zip";
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);

    setStatus(els.batchStatus, `Downloaded ZIP with ${items.length} clips.`, "ok");
  } catch (err) {
    setStatus(els.batchStatus, err.message, "err");
  } finally {
    els.batchRunBtn.disabled = false;
  }
});

// Init
els.apiBaseUrl.textContent = `${window.location.origin}/v1`;
updateCharCount();
loadVoices();