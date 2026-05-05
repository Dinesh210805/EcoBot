# EcoBot Frontend: Complete Page-by-Page Design & Asset Specification

This document serves as the absolute blueprint for engineering the EcoBot frontend. It dictates the rigorous design rules, the specific color palette, typography pairs, page layouts, and the exact AI generative prompts needed to create the assets.

---

## 1. Global Design System

### 1.1. Color Palette (Organic Maximalism)
Instead of defaulting to generic flat colors, we use lighting and semantic tokens that feel organic.
*   **Background (Forest Shadows):** `#0A140E` — Deep, almost black, pine green.
*   **Foreground / Text (Morning Mist):** `#F2F7F4` — Soft, off-white with a hint of mint.
*   **Primary Accent (Bioluminescence):** `#84E09B` — A glowing, energetic green for active states and primary buttons.
*   **Secondary Accent (Sunlight):** `#EAD2AC` — Used for highlights or secondary informative text.
*   **Category Semantic Colors (Mapping backend values):**
    *   `wet_waste` (Green): `#5B8266`
    *   `dry_waste` (Blue): `#3B82F6`
    *   `hazardous` / `e_waste` (Red): `#E56B6F`
    *   `sanitary` (Black): `#2B2B2B`
    *   `construction` / `non_recyclable` (Grey): `#8C8C8C`
*   **Surface (Glassmorphism):** `rgba(242, 247, 244, 0.05)` with `backdrop-blur-xl` and a `1px` border of `rgba(255, 255, 255, 0.1)`.

### 1.2. Typography
*   **Display / Headings:** **Ogg** (or *Playfair Display* / *PP Fragment* as fallback). It provides organic, sweeping, editorial elegance corresponding to untamed nature.
*   **Body / Data:** **Geist Mono** (or *Satoshi*). Utilitarian, highly legible technical sans-serif to display the data arriving from the EcoBot FastAPI backend.

---

## 2. Page 1: Landing (Scrollytelling Experience)

This page uses **GSAP ScrollTrigger** + an HTML5 `<canvas>` to tie a video frame sequence directly to the user's scrollbar.

### Section 1.1: The Descent (Hero)
*   **UI:** Extremely minimal. Huge `Ogg` heading: **"Classify the Waste. Uncover the Forest."** A single scroll indicator dot pulsing at the bottom.
*   **Background Element:** A canvas rendering of a 60fps video sequence falling through a forest canopy.
*   **Asset Type:** Video `.mp4` (exported to `.webp` frame sequence).
*   **AI Video Prompt (Runway Gen-3 / Luma Dream Machine):** 
    > *"FPV drone shot diving vertically down through a lush, dense, sunlit ancient forest canopy. Ethereal morning sunlight rays piercing through thick green leaves. Studio Ghibli mixed with Vinland Saga aesthetic, photorealistic anime, highly detailed, slow continuous motion, 4k, 60fps."*

### Section 1.2: The Disruption (Sticky Pinned Section)
*   **UI:** The scroll pauses the background video. A frosted glassmorphism card slides in from the left: *"Nature doesn't make waste. We do."*
*   **Background Element:** The video sequence halts precisely as the camera reaches the forest floor, landing on a beautiful mossy ground where a single piece of human trash lies.
*   **Asset Type:** Wait for Gen-3 video to hit the ground, OR use a static highly detailed Midjourney image for a smooth crossfade.
*   **AI Image Prompt (Midjourney v6):** 
    > *"A breathtaking ancient forest floor covered in soft glowing green moss. Resting cleanly on the moss is a single crumpled, rusted metallic soda can. Cinematic lighting, macro photography, Unreal Engine 5 render style, ethereal, Studio Ghibli lighting, --ar 16:9 --v 6.0"*

### Section 1.3: The Interface Reveal (Product Demo)
*   **UI:** A sleek, 3D borderless smartphone frame slides up into the center of the screen. The background goes `.blur-md`. As the user scrolls, the UI inside the phone automatically types out text and demonstrates the EcoBot API.
    *   *Scroll Frame 1:* Types "old newspaper" -> hits the `/classify/text` API.
    *   *Scroll Frame 2:* Card flips to show `category: dry_waste`.
    *   *Scroll Frame 3:* Map drops down demonstrating `/facilities` API.

### Section 1.4: The Blueprint (Bento Grid View)
*   **UI:** The phone scales down and vanishes. A 3x3 Bento Grid layout slides in. The cards have heavy backdrop blur.
    *   *Top-left:* "Powered by LLaMA 3 & Gemini".
    *   *Top-right:* Dynamic stat counter ("142 Disposal Guidelines").
    *   *Bottom-wide:* Voice Classification visualizer (Audio waveforms).
*   **Background Element:** A still, sweeping landscape.
*   **AI Image Prompt (Midjourney v6):**
    > *"A vast, breathtaking anime-style landscape of a clear blue sky over a pristine, endless green valley. Studio Ghibli aesthetic, fluffy white clouds, gentle lighting, masterpiece, wide angle, --ar 16:9 --style raw"*

### Section 1.5: Footer (Call to action)
*   **UI:** Large CTA button: **"Open EcoBot"** (links to `/app`). Button uses a magnetic hover effect.

---

## 3. Page 2: The Application App (`/app`)

This is the functional page connected to the FastAPI backend. It drops the heavy video canvas for strict, high-performance utility, retaining the glass and nature aesthetic.

### 3.1. Layout Structure
*   **Sidebar (Left):** Glassmorphic panel containing Chat History (session IDs), "New Scan", and User Location toggle.
*   **Main Stage (Center):** The Chat / Classification interface.
*   **Context Panel (Right - Collapsible):** Facility Map & Environmental Facts.

### 3.2. The Input Zone (Action Bar)
Pinned to the bottom center, a sleek floating pill container.
*   **Text Input:** Auto-growing textarea.
*   **Camera Button:** Triggers `POST /classify/image`. Opens a sleek modal with a live webcam feed.
*   **Microphone Button:** Triggers `POST /classify/voice`. On hold, it pulses with `#84E09B` bioluminescent waves.

### 3.3. Classification Result Card UI
When the API returns a response, a beautifully structured card drops in using `framer-motion`:
*   **Header:** Shows the item name ("Plastic Bottle").
*   **Color Strip:** A distinct neon glow based on `bin_color` (e.g., `#3B82F6` for Blue).
*   **Details:** `prep_steps` displayed as clean bullet points with SVG checkmarks.
*   **Action:** If `facilities` exists, a "View on Map" button highlights.

### 3.4. AI Assets for Application UI
We need generic beautiful 3D icons for the core categories to display in the UI when real pictures aren't provided.
*   **Category Icon Prompts (Midjourney v6):**
    *   *Wet Waste:* > *"A stylized, aesthetic 3D icon of a beautiful, fresh green apple core resting on a pristine leaf. Soft claymorphism, glassmorphism, studio lighting, isolated on black background, --v 6.0"*
    *   *E-Waste:* > *"A stylized, aesthetic 3D icon of a cracked circuit board glowing faintly with blue light. Soft claymorphism, glassmorphism, studio lighting, isolated on black background, --v 6.0"*

---

## 4. Engineering Asset Checklist

If we begin the build, we will run the following steps:

1. **Frontend Bootstrapping:**
   `npx create-next-app@latest ecobot-web`
   `npx shadcn-ui@latest init`
2. **Package Installations:**
   `npm install framer-motion gsap @studio-freight/react-lenis lucide-react`
3. **Asset Pre-processing Pipeline:**
   * Generate video via Runway.
   * Run ffmpeg script: `ffmpeg -i descent.mp4 -vf scale=1920:-1 -r 30 assets/frames/frame_%04d.webp`
4. **API Integration:**
   * Create `lib/api.ts` wrapping the Python FastAPI (`http://localhost:8000/api/v1/`).
   * Interface types matching `backend/models/responses.py` (e.g. `ClassificationResponse`).