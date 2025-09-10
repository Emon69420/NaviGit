# 💻 Project Dashboard – this project

---

## 1️⃣ Summary / About  
HazMap is a React Native Expo application focused on **real‑time environmental monitoring** and **hazard mapping**.  
* **Core Features** – Interactive Google Maps, live air‑quality graphs, wildfire‑risk prediction, evacuation route planning, and emergency notifications.  
* **Authentication** – Supabase for user accounts, role‑based sign‐up (citizen, official, responder).  
* **Background processing** – Expo Background Fetch runs every 10 min to query weather, air‑quality, elevation, and a custom wildfire‑prediction API, then pushes notifications for High/Extreme risk.  
* **Tech stack** – React Native 0.79, Expo 53, TypeScript 5.8, React Navigation (Expo Router), React‑Context API, Map libraries (react‑native‑maps, mapbox‑gl), Supabase SDK, Lottie animations, Lucide icons, and various Expo plugins (location, notifications, task manager).

---

## 2️⃣ Possible Vulnerabilities

| Area | Risk | Why | Mitigation |
|------|------|-----|------------|
| **API Key Leakage** | Hard‑coded placeholders (e.g. `API_KEY_HERE`, `SUPABASE_URL_HERE`). | If accidentally committed, attackers can abuse Google and Supabase services. | Move all secrets to a `.env` file and use `expo-constants`/`expo-config` to inject at build time. |
| **Location & Permissions** | Background location access (`ACCESS_BACKGROUND_LOCATION`). | Mis‑configured permissions can expose user data or fail on iOS. | Use runtime checks, request permissions only when needed, and handle denied states gracefully. |
| **Background Task Errors** | Unsanitized network responses in `backgroundTasks.ts`. | Poor error-handling could crash the task or silently fail, leading to missing alerts. | Wrap all external calls in try/catch with retry logic and clear error logging. |
| **Supabase Auth** | `persistSession: true` + `detectSessionInUrl: false` may keep sessions in storage. | If storage is compromised, credentials can be used. | Use secure storage (`expo-secure-store`), rotate tokens, enforce session expiry. |
| **Unvalidated Input** | Sign‑up and login forms lack server‑side validation beyond presence checks. | Malicious data could cause unexpected behavior after integration. | Add validation (e.g., email regex, password strength) before calling Supabase. |
| **Outdated Dependencies** | Some dependencies (e.g., `react` 19.0.0 in the dev environment, `mapbox-gl` 3.13.0) may contain known bugs or vulnerabilities. | External libraries occasionally have security advisories. | Audit with `npm audit` and upgrade to the latest compatible versions. |

---

## 3️⃣ Stale / Out‑of‑Date Dependencies

* **`react` / `react-native`** – The project uses `react@19` (Dev only) while Expo 53 is built for React 18. This mismatch can cause runtime errors.  
* **`react-dom`** – Included but not required for a purely mobile app; likely only used for web builds. Keep it to the minimal version compatible with Expo Web.  
* **`react-map-gl`** – Still on `^8.0.4`. Modern Expo setups favor `react-native-maps` or `mapbox-gl`. Check that it is actually used; if not, remove.  
* **`mapbox-gl`** – v3.13.0 might be older; the current major is v4.x.  
* **`expo`** ≥ 53 is current, but some plugins (`expo-router`, `expo-task-manager`, `expo-background-fetch`) have newer minor releases.  
* **`lucide-react-native`** – Version `^0.475.0` may have newer patches; consider pinning to a minor update.

Run `npm outdated` and `npm audit` to confirm any other stale or vulnerable packages.

---

## 4️⃣ Suggestions for Improvement

1. **Secure Configuration**  
   * Strictly separate production vs. development environment keys via `.env`.  
   * Leverage Expo’s `expo-constants` and the new *runtime config* feature to inject secrets safely.

2. **Dependency Hygiene**  
   * Align React/React‑Native to versions supported by Expo 53 (React 18).  
   * Remove unnecessary packages (`react-dom`, `react-map-gl` if unused).  
   * Adopt the latest Expo SDK (`npm install expo@latest` and update related plugins).

3. **Background Task Robustness**  
   * Add exponential backoff for API failures.  
   * Persist the last successful check to avoid duplicate notifications.  
   * Log task results to a central analytics endpoint (e.g., Supabase logs).

4. **Testing & Continuous Integration**  
   * Add unit tests for hooks (`useAuth`, `useFrameworkReady`) and services (`backgroundTasks.ts`).  
   * Configure GitHub Actions to run `npm ci`, `npm run lint`, `npm test`, and `npm run build:web`.  
   * Use `eslint-plugin-security` for runtime security checks.

5. **Accessibility**  
   * Provide `accessibilityLabel` and `accessibilityHint` on interactive elements.  
   * Ensure color contrast on map overlays and UI components.

6. **User Feedback**  
   * Provide toast notifications when background monitoring is toggled on/off.  
   * Show a loading indicator during first launch when fetching background data.

7. **Component Organization**  
   * Move reusable UI pieces (e.g., `AuthForm`, `ProfileHeader`) into `components/ui`.  
   * Separate route files into a `navigation/` folder for clearer navigation hierarchy.

---

## 5️⃣ Best Practices Observed (✓) vs. Missing (✗)

| Practice | Observed | Notes |
|----------|----------|-------|
| **TypeScript strict mode** | ✓ | `tsconfig.json` enforces strict typing. |
| **Environment variable usage** | ✗ | Placeholders are hard‑coded; no `.env` integration. |
| **Secure storage of tokens** | ✗ | Supabase uses AsyncStorage, but no encryption; consider `expo-secure-store`. |
| **Component-level styling** | ✓ | Inline StyleSheet objects used throughout. |
| **Navigation structure** | ✓ | Expo Router with `Stack` screens organizes auth and main flows. |
| **Error handling** | ✗ | Many API calls lack try/catch or user feedback. |
| **Code linting/formatting** | ✓ | Prettier configured; `lint` script available. |
| **Unit testing** | ✗ | No tests present; consider Jest + React Testing Library for RN. |
| **Accessibility** | ✗ | No accessibility props; add for text, buttons, and inputs. |
| **Documentation** | ✗ | README covers most aspects, but in‑code comments are minimal. |
| **Background task registration** | ✓ | `startBackgroundFetch` called on app ready. |

---

## 6️⃣ Code Quality Assessment

* **Readability** – Components are reasonably organized, but some modules (e.g., `backgroundTasks.ts`) could be structured into smaller reusable functions.  
* **Naming** – Clear component names (`LoginScreen`, `SignUpScreen`) and hooks (`useAuthContext`). However, service functions could use more descriptive names.  
* **Duplication** – The sign‑in and sign‑up forms share similar UI; extract a common `AuthForm` component to reduce duplication.  
* **Prop Validation** – No PropTypes or runtime validation; rely on TypeScript strictly.  
* **Comments** – Sparse comments; add at least one line per function/explanation of side‑effects, especially in background logic.  
* **Error Handling** – UI alerts are used for auth errors, but network failures in background tasks are silent.  
* **Test Coverage** – None; add tests for critical paths (auth flow, background task logic).  

Overall, the codebase follows the typical structure for Expo projects but would benefit from tighter security config, more robust error handling, and