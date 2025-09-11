# Project Dashboard – *This Project*

Below is a concise, visual‑friendly panel that summarizes the current state of the codebase, highlights risks, offers concrete improvements, and provides an actionable onboarding guide for new contributors.

---

## 📌 Summary / About  
- **Purpose:** Real‑time American Sign Language (ASL) recognition system running on a webcam.  
- **Core Flow:**  
  1. **Data Capture:** `collectionData.py` writes hand‑pose images to `Image/` folders.  
  2. **Keypoint Extraction:** `data.py` loads images → mediapipe → saves 63‑dim NumPy arrays (`MP_Data/<action>/<sequence>/<frame>.npy`).  
  3. **Model Training:** `trainmodel.py` builds a 3‑layer LSTM network, trains on the extracted sequences, and persists `model.h5` + `model.json`.  
  4. **Inference:** `app.py` streams live video, runs mediapipe, feeds 30‑frame windows to the LSTM, and displays predicted ASL symbols in a confidence UI.  
- **Tech Stack:**  
  - **Python 3.9+** (assumed)  
  - **OpenCV** for camera + UI  
  - **Mediapipe** for hand landmarks  
  - **TensorFlow/Keras** (both `tf.keras` and legacy `keras` packages used)  
  - **NumPy, sklearn** for preprocessing  
  - **TensorBoard** for training logs  

---

## ⚠️ Potential Vulnerabilities  
| Area | Risk | Why it matters | Mitigation |
|------|------|----------------|------------|
| **File I/O & Path Handling** | Hard‑coded relative paths (e.g. `Image/`, `MP_Data/`) can break under different working directories; missing dirs cause crashes. | Denial of service or data loss during build / deployment. | Use `pathlib` & environment‑based config; validate directories before use. |
| **External Library Versions** | Mixing `keras` (stand‑alone) and `tensorflow.keras` may import conflicting sub‑modules, leading to inconsistent layer definitions. | Unexpected runtime errors, version drift. | Pin a single Keras version via `tensorflow>=2.x`; remove legacy imports. |
| **OpenCV Without Security Checks** | `cv2.VideoCapture(0)` opens a device that could be exploited if the app is exposed over a network. | Privilege escalation or unauthorized camera access. | Disable network exposure or wrap with authentication if web‑based. |
| **No Input Validation** | Directly using `cv2.imread('Image/{}/{}.png')` may load corrupted or malicious files. | Runtime errors, potential exploitation. | Add file existence & format checks; use secure image parsing. |
| **Hard‑coded Thresholds** | `threshold = 0.8` is static; no tolerance to varying lighting conditions. | Poor usability / false positives. | Allow dynamic calibration or adaptive thresholding. |

---

## 📦 Stale / Outdated Dependencies  
| Package | Current Usage | Suggested Version | Notes |
|---------|---------------|-------------------|-------|
| **keras** | Imported via `import keras` | Remove; rely on `tensorflow.keras` | Avoid duplicate installation paths. |
| **tensorflow** | Implicit (used as `from keras import ...`) | Pin to the latest stable minor release (e.g., 2.13.0) | Guarantees API stability. |
| **opencv‑python** | Directly imported as `cv2` | Pin to a version compatible with mediapipe (>=4.8) | Prevent build/compatibility issues. |
| **mediapipe** | Used via `mp.solutions` | Pin to the latest (e.g., 0.10.0) | Ensures correct landmark outputs. |
| **sklearn** | Used only for `train_test_split` | Pin to a recent release (>=1.2) | Compatibility with numpy. |

Add a `requirements.txt` or `pyproject.toml` specifying these pins.  

---

## 🚀 Suggestions for Improvement  

| Category | Recommendation | ROI |
|----------|----------------|-----|
| **Project Organization** | Create a top‑level `src/` package, move all modules there. Adopt a `setup.py` or PEP‑517 build. | Long‑term maintainability. |
| **Configuration** | Extract constants (`actions`, `sequence_length`, file paths) into an `config.yaml` or `constants.py`. | Easier experimentation & multi‑deployment. |
| **Logging** | Replace `print()` statements with Python `logging` module. | Better debug traceability, testability. |
| **Error Handling** | Wrap file ops and model loading in try/except blocks; propagate user‑friendly messages. | Prevent crashes in production. |
| **Unit Tests** | Add test suite for `extract_keypoints`, data directory creation, and model predictions. | Confidence for refactors. |
| **CI/CD** | Configure GitHub Actions: lint (flake8, black), unit tests, and automatic TensorBoard logs. | Rapid feedback loop. |
| **Documentation** | Include a comprehensive `README.md` covering: project goal, directory tree, data prep steps, training, inference, and troubleshooting. | Low onboarding barrier. |
| **Code Style** | Run `black`, `isort`, and `pylint` to enforce PEP8 + type hints. | Cleaner code, fewer bugs. |
| **Data Scaling** | Move from hard‑coded 50 frame windows to `ARG_MAX_FRAMES` variable, optionally support variable length via attention. | Future‑proofing for richer gestures. |

---

## 🔎 Best Practices Observed & Lacking  

| Best Practice | Present? | Notes |
|---------------|----------|-------|
| **Modular Design** | ❌ | Logic split is uneven; functions missing docstrings. |
| **Separation of Concerns** | ❌ | Training, data prep, inference all in top level scripts. |
| **Configuration Management** | ❌ | Hard‑coded constants in code. |
| **Error Handling** | ❌ | Minimal try/except; silent pass in `app.py`. |
| **Logging** | ❌ | Uses `print`; no severity levels. |
| **Testing** | ❌ | No tests. |
| **Version Control** | ✅ | Repo files present, but CI/branch protection not yet set. |

---

## 👨‍💻 Code Quality Snapshot  

- **Readability** – Variable names mostly clear, but mixed styles (`action` vs `actions` vs `no_sequences`).  
- **Docstrings & Comments** – Almost none; future contributors may mis‑interpret functions.  
- **Naming Conventions** – Uses snake_case; some functions use camelCase (`mediapipe_detection`).  
- **Repetition** – Manual key mapping in `collectionData.py` could be loop‑generated.  

**Action Items:**  
1. Add module‑level docstrings explaining purpose of each file.  
2. Standardize function naming convention.  
3. Replace repetitive key‑counting with a dictionary comprehension.  

---

## 📚 Onboarding Flow for New Developers

1. **Clone & Set Up Virtualenv**  
   ```bash
   git clone <repo-url>
   cd emon69420-signlanginter
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt  # (include pip install -r requirements.txt)
   ```
2. **Verify Dependencies**  
   Run `pip check` to ensure no conflicts.  
3. **Prepare Data**  
   - Run `python -m signLangInt.collectionData` to capture raw images.  
   - Or populate `Image/<action>/<sequence>/` manually.
4. **Generate Keypoints**  
   ```bash
   python -m signLangInt.data
   ```
   This will read images, run Mediapipe, and output NumPy files under `MP_Data/`.
5. **Train Model**  
   ```bash
   python -m signLangInt.trainmodel
   ```
   - Training logs are under `Logs/train/`; view with `tensorboard --logdir=Logs/train`.
6. **Run Inference**  
   ```bash
   python -