# 📊 HazMap Project Dashboard

**Repo:** `emon69420-hazmapapp`  
**Tech Stack:** React Native (Expo), TypeScript, Supabase, Google Maps APIs, Lottie, Expo Background Fetch  

---

## 🔍 Summary / About

HazMap is a mobile-first application that visualizes real‑time environmental data—air quality, wildfire risk, satellite imagery, and evacuation routes—on interactive maps.  
Key features:

| Feature | Details |
|---------|---------|
| **Mapping** | Google Maps, dynamic hazard overlays, custom styling |
| **Air Quality** | Live pollutant breakdown, Lottie animations tailored to AQI |
| **Wildfire Prediction** | Background fetch every 10 min, integration with a remote prediction API |
| **Evacuation Planning** | Dynamic routes, emergency contacts |
| **Auth** | Supabase‑powered email/password, role‑based (citizen, official, responder) |
| **State** | React Context + hooks, local AsyncStorage persistence |
| **Multiplatform** | Works on iOS, Android, and web (Expo) |

The repo contains a **frontend** (Expo React Native) and an **API backend** (`HazEnd - Flask Backend/`) written in Flask.

---

## ⚠️ Possible Vulnerabilities

| Category | Risk | Evidence | Mitigation |
|----------|------|----------|------------|
| **API Key Exposure** | Public keys in `app.json`/`eas.json` | `API_KEY_HERE` placeholder; code comments mention to replace. | Keep keys in a `.env` file; use Expo Constants to inject. |
| **CORS / Network** | Hard‑coded Flask endpoint (`http://34.130.243.115:5000/gee-data`) | Not protected, no token. | Add Auth token or API key validation on server. |
| **Background Task** | Possible location leaks | Task runs in background with location permission. | Use user opt‑in, encrypt payloads. |
| **Supabase Auth** | AutoRefreshToken may allow long‑term session if not revoked | `autoRefreshToken: true` | Ensure session is invalidated on logout. |
| **Dependency Vulnerabilities** | Several libraries (expo‑background-fetch, expo‑notifications) have known CVEs | Not audited. | Run `npm audit`. |
| **HTTPS enforcement** | Backend uses HTTP, no TLS. | Endpoint hard‑coded HTTP. | Move to HTTPS with proper certs. |
| **Lottie Files** | No sanitization (but static). | `assets/lottie/*.json` | Ensure they’re from trusted source. |

---

## 📦 Stale / Out‑of‑Date Dependencies

Based on `package.json`, the following packages are more than a year old or have newer major/minor releases:

| Package | Current | Latest | Notes |
|---------|---------|--------|-------|
| `expo` | 53.0.20 | 54.x.x | Expo 54 released; may bring breaking changes. |
| `react` | 19.0.0 | 19.0.0 (currently) | Awaiting next major after 20. |
| `react-native` | 0.79.5 | 0.80.x | Minor. |
| `expo-background-fetch` | ~13.1.6 | 13.2.x | Minor. |
| `expo-task-manager` | ~13.1.6 | 13.2.x | Minor. |
| `expo-notifications` | 0.31.4 | 0.37.x | Major improvement. |
| `react-native-maps` | 1.20.1 | 1.29.x | Significant bug fixes. |
| `react-native-paper` | 5.14.5 | 5.20.x | Adds components & better theming. |

**Recommendation:** Run `npm outdated` and plan an upgrade cycle, prioritizing packages that provide security patches.

---

## 🛠️ Suggestions for Improvements

| Area | Action |
|------|--------|
| **Environment Vars** | Use Expo Config‑Plugins to inject `EXPO_PUBLIC_*` variables; remove placeholder strings. |
| **Background Tasks** | Migrate from `expo-background-fetch` to `expo-task-manager + expo-location` with **Task Manager** (recommended) for more reliable scheduling. |
| **Testing** | Add Jest unit tests for hooks (`useAuth`, `useFrameworkReady`) and services (backgroundTasks). |
| **Type Safety** | Create explicit types for API responses; move environment types into `src/types`. |
| **Security** | Store private keys in SecureStore; enforce TLS in Flask backend. |
| **Accessibility** | Add `accessibilityLabel` props to buttons; respect `prefers-reduced-motion` for animations. |
| **Performance** | Cache map tiles offline; use React Native Performance Monitor. |
| **Code Splitting** | Move heavy components to lazy‑loaded screens. |
| **CI/CD** | Add GitHub Actions to lint, test, and build for iOS/Android. |
| **Documentation** | Expand `README` with step‑by‑step onboarding and example `.env`. |

---

## 📌 Best Practices Observed

| Practice | Where & How |
|----------|-------------|
| **TypeScript** | Strict mode enabled; almost all files typed. |
| **React Native Router** | Using `expo-router` with file‑based routes. |
| **Context Separation** | `AuthContext`, `LocationContext`. |
| **AsyncStorage for Session** | Uses `supabase-js` storage plugin. |
| **Splash/Status Bar** | Properly configured in `_layout.tsx`. |
| **Asset Organization** | Static assets in `assets/` (images, lottie). |
| **Linting** | `npm run lint` script available. |

---

## ⚡ Coding Quality

- **Pros**  
  - Consistent naming conventions (`useAuth`, `useLocation`).  
  - UI components are reusable (`LoadingScreen`).  
  - Separation of concerns: `services/backgroundTasks.ts` contains business logic.

- **Cons**  
  - Several hard‑coded strings (`API_KEY_HERE`) in code.  
  - Mixed use of inline styles and style objects; could benefit from a UI‑theme provider.  
  - Lack of error handling in background tasks (e.g., network failures).  
  - Mixed return types in `signIn`/`signUp` (`data, error`) – could benefit from `Result<T>` type.

---

## 🌱 Onboarding for New Developers

1. **Prerequisites**  
   - Node.js v18+  
   - Expo CLI (`npm install -g expo-cli`)  
   - Android/iOS dev environment (Android Studio, Xcode)  

2. **Clone & Install**  
   ```bash
   git clone https://github.com/yourusername/emon69420-hazmapapp.git
   cd emon69420-hazmapapp
   npm install
   ```

3. **Setup Environment**  
   - Create a `.env` file in the root with:  
     ```
     EXPO_PUBLIC_GOOGLE_MAPS_API_KEY=...
     EXPO_PUBLIC_SUPABASE_URL=...
     EXPO_PUBLIC_SUPABASE_KEY=...
     ```
   - Store any secret keys in `expo-secure-store` or AWS Secret Manager if deploying.

4. **Run**  
   ```bash
   npx expo start
   ```
   Scan QR with Expo Go or run `npx expo start --android`.

5. **Folder Overview**  
   - `app/` – Screens and router layouts.  
   - `components/` – Re‑usable UI.  
   - `contexts/`, `hooks/` – State and app logic.  
   - `services/` – API calls, background tasks.  
   - `supabaseClient.ts` – Supabase initialization.  
   - `HazEnd - Flask Backend/` – Python API; run separately (`pip install -r requirements.txt`).  

6. **Development Workflow**  
   - Branch per feature (`feature/*`).  
   - Commit with clear messages.  
   - Pull requests required for merges to `main`.  

7. **Testing**  
   - Run `npm test` when tests are added.  
   - Write tests for new hooks/services.  

8. **Lint & Format**  
   - `npm run lint`  
   - `npm run format` (if Prettier script added).  

9. **Contribution**  
   - Follow the contributing guidelines in the repo.  
   - Review issues and PR templates.  

---

*This dashboard provides a snapshot of the repository’s state, health, and next steps. Happy coding!*