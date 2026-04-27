/* ── State ────────────────────────────────────────── */
let selectedFiles = [];  // Array of File objects (managed manually for remove support)

const fileInput    = document.getElementById("file-input");
const dropZone     = document.getElementById("drop-zone");
const fileList     = document.getElementById("file-list");
const generateBtn  = document.getElementById("generate-btn");
const statusText   = document.getElementById("status-text");
const resultsSection = document.getElementById("results-section");
const resultsGrid  = document.getElementById("results-grid");
const downloadAllBtn = document.getElementById("download-all-btn");

/* ── Input validation ───────────────────────────── */
const PARAM_BOUNDS = {
  size:   { min: 32,  max: 512,  step: 1   },
  frames: { min: 4,   max: 60,   step: 1   },
  speed:  { min: 0.1, max: 3.0,  step: 0.1 },
  height: { min: 0,   max: 64,   step: 1   },
  angle:  { min: 0,   max: 15,   step: 0.5 },
};

function validateInput(id) {
  const input = document.getElementById(id);
  const warn = document.getElementById(id + "-warn");
  if (!input || !warn) return;

  const bounds = PARAM_BOUNDS[id];
  const val = parseFloat(input.value);

  if (isNaN(val)) {
    warn.textContent = "Enter a number";
    input.classList.add("invalid");
    return;
  }
  if (val < bounds.min) {
    warn.textContent = `Min is ${bounds.min}`;
    input.classList.add("invalid");
    return;
  }
  if (val > bounds.max) {
    warn.textContent = `Max is ${bounds.max}`;
    input.classList.add("invalid");
    return;
  }

  warn.textContent = "";
  input.classList.remove("invalid");
}

for (const id of Object.keys(PARAM_BOUNDS)) {
  const input = document.getElementById(id);
  if (input) {
    input.addEventListener("input", () => validateInput(id));
    input.addEventListener("change", () => {
      const bounds = PARAM_BOUNDS[id];
      let val = parseFloat(input.value);
      if (isNaN(val)) val = bounds.min;
      val = Math.max(bounds.min, Math.min(bounds.max, val));
      val = Math.round(val / bounds.step) * bounds.step;
      input.value = parseFloat(val.toFixed(4));
      validateInput(id);
    });
  }
}

/* ── Animation type switching ────────────────────── */
function updateAnimationParams() {
  const anim = document.querySelector('input[name="animation"]:checked').value;
  document.querySelectorAll(".param-group[data-for]").forEach(group => {
    const targets = group.getAttribute("data-for").split(" ");
    group.style.display = targets.includes(anim) ? "" : "none";
  });
}

document.querySelectorAll('input[name="animation"]').forEach(radio => {
  radio.addEventListener("change", updateAnimationParams);
});
updateAnimationParams();

/* ── File selection ──────────────────────────────── */
fileInput.addEventListener("change", () => {
  addFiles(fileInput.files);
  fileInput.value = "";          // allow re-selecting the same files
});

/* Drag and drop */
dropZone.addEventListener("dragover", (e) => {
  e.preventDefault();
  dropZone.classList.add("dragover");
});
dropZone.addEventListener("dragleave", () => {
  dropZone.classList.remove("dragover");
});
dropZone.addEventListener("drop", (e) => {
  e.preventDefault();
  dropZone.classList.remove("dragover");
  addFiles(e.dataTransfer.files);
});

/* Clicking the zone also opens the picker */
dropZone.addEventListener("click", (e) => {
  if (e.target.closest(".file-btn")) return;   // let the label handle it
  fileInput.click();
});

function addFiles(fileListObj) {
  for (const f of fileListObj) {
    if (selectedFiles.length >= 20) break;
    // skip duplicates by name+size
    if (selectedFiles.some(s => s.name === f.name && s.size === f.size)) continue;
    selectedFiles.push(f);
  }
  renderFileList();
}

function removeFile(index) {
  selectedFiles.splice(index, 1);
  renderFileList();
}

function renderFileList() {
  fileList.innerHTML = "";
  selectedFiles.forEach((f, i) => {
    const thumb = document.createElement("div");
    thumb.className = "file-thumb";

    const img = document.createElement("img");
    img.src = URL.createObjectURL(f);
    img.onload = () => URL.revokeObjectURL(img.src);

    const btn = document.createElement("button");
    btn.className = "remove-btn";
    btn.textContent = "×";
    btn.title = "Remove";
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      removeFile(i);
    });

    thumb.appendChild(img);
    thumb.appendChild(btn);
    fileList.appendChild(thumb);
  });

  generateBtn.disabled = selectedFiles.length === 0;
}

/* ── Generate ────────────────────────────────────── */
generateBtn.addEventListener("click", async () => {
  if (selectedFiles.length === 0) return;

  const formData = new FormData();
  for (const f of selectedFiles) {
    formData.append("files[]", f);
  }

  // Collect parameters
  const fmt = document.querySelector('input[name="format"]:checked').value;
  const anim = document.querySelector('input[name="animation"]:checked').value;
  formData.append("format", fmt);
  formData.append("animation", anim);
  for (const id of ["size", "frames", "speed", "height", "angle"]) {
    formData.append(id, document.getElementById(id).value);
  }

  // UI loading state
  generateBtn.classList.add("loading");
  generateBtn.textContent = "Generating…";
  generateBtn.disabled = true;
  statusText.textContent = `Processing ${selectedFiles.length} image${selectedFiles.length > 1 ? "s" : ""}…`;
  resultsSection.hidden = true;

  try {
    const resp = await fetch("/api/generate", { method: "POST", body: formData });
    const data = await resp.json();

    if (data.error) {
      statusText.textContent = "Error: " + data.error;
      return;
    }

    renderResults(data.results);
    statusText.textContent = `Done – ${data.results.length} result${data.results.length > 1 ? "s" : ""}`;
  } catch (err) {
    statusText.textContent = "Request failed: " + err.message;
  } finally {
    generateBtn.classList.remove("loading");
    generateBtn.textContent = "Generate";
    generateBtn.disabled = selectedFiles.length === 0;
  }
});

/* ── Results ─────────────────────────────────────── */
let lastResults = [];

function renderResults(results) {
  lastResults = results;
  resultsGrid.innerHTML = "";
  resultsSection.hidden = false;

  const successCount = results.filter(r => !r.error).length;
  downloadAllBtn.hidden = successCount < 2;

  for (const r of results) {
    const card = document.createElement("div");
    card.className = "result-card";

    if (r.error) {
      card.innerHTML =
        `<p class="filename">${esc(r.filename)}</p>` +
        `<p class="error-msg">${esc(r.error)}</p>`;
    } else {
      const dataUri = `data:${r.content_type};base64,${r.data}`;
      card.innerHTML =
        `<img src="${dataUri}" alt="${esc(r.filename)}">` +
        `<p class="filename">${esc(r.filename)}</p>` +
        `<p class="size ${r.size_kb < 256 ? "ok" : "warn"}">${r.size_kb} KB${r.size_kb >= 256 ? " (over Discord limit)" : ""}</p>` +
        `<a class="download-btn" href="${dataUri}" download="${esc(r.filename)}">Download</a>`;
    }

    resultsGrid.appendChild(card);
  }
}

/* ── Download All ────────────────────────────────── */
downloadAllBtn.addEventListener("click", () => {
  for (const r of lastResults) {
    if (r.error) continue;
    const a = document.createElement("a");
    a.href = `data:${r.content_type};base64,${r.data}`;
    a.download = r.filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  }
});

/* ── Util ────────────────────────────────────────── */
function esc(s) {
  const d = document.createElement("div");
  d.textContent = s;
  return d.innerHTML;
}
