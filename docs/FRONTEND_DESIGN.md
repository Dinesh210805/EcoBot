# EcoBot — Frontend Motion Design Concept

## 1. Brand Identity
**Name:** EcoBot
**Tagline Options:**
1. *Nature's Intelligence, In Your Hands.*
2. *Classify. Recycle. Restore.*
3. *Harmony with nature, powered by AI.*

## 2. Core Visual Aesthetic
**"Cinematic Nature meets Apple Minimalism"**
* **Backgrounds:** Inspired by the lush, breathtaking natural environments of anime like *Vinland Saga* or Studio Ghibli. Think vibrant greens, morning sun rays piercing through forest canopies, and crystal-clear streams.
* **Foreground UI:** Ultra-clean, Apple-style glassmorphism. Subtle blurs, thin white borders, and sleek, minimalist typography (e.g., Inter or SF Pro). Shadcn UI components customized with rounded corners and soft shadows so they feel like they are floating in the environment.

## 3. Motion & Scroll Engine (The "Apple" Feel)
* **Scrollytelling:** Using **GSAP ScrollTrigger** and **Framer Motion**, the scroll wheel will control the timeline of the page rather than just moving content up and down.
* **Video-to-Frames Scrubbing:** We will generate high-fidelity AI videos of natural landscapes panning or moving forward. We convert these videos to image sequences and render them on an HTML5 `<canvas>`. As the user scrolls, the frames advance, creating a seamless, high-performance cinematic journey through a forest.

## 4. Page Flow & Transitions

### Section 1: The Awakening (Hero)
* **Visual:** A stunning, animated sunrise over an untouched, lush forest valley. 
* **UI:** The EcoBot logo fades in gracefully. As the user begins to scroll, the text dissolves, and the "camera" (the background video sequence) dives down into the forest canopy.
* **Transition:** The canopy leaves part, revealing a clearing.

### Section 2: The Core Mission
* **Visual:** The clearing. As you scroll, a subtle shadowy overlay or a few pieces of out-of-place waste appear.
* **UI:** A glassmorphic card slides up smoothly: *"Every piece of waste has a home. We help you find it."*

### Section 3: The EcoBot Interface (Sticky Scroll)
* **Visual:** The background softly blurs. A sleek 3D smartphone mockup or an elegant chat interface locks into the center of the screen (Sticky positioning).
* **Interaction:** As the user continues scrolling down, the background video slowly shifts to a cleaner, brighter area of the forest. Meanwhile, the UI inside the phone mockup animates between EcoBot's core features:
  1. *Text Input* typing animation.
  2. *Camera interface* scanning a plastic bottle.
  3. *Voice recording* animation pulsing.

### Section 4: The Impact (Data & Facilities)
* **Visual:** The camera emerges from the forest to a vast, open landscape with a clear blue sky.
* **UI:** A beautifully animated counter ticks up (waste saved, trees planted). A floating, interactive map (or abstract 3D globe) shows glowing dots representing recycling facilities connected by EcoBot.

### Section 5: Call to Action (Footer)
* **Visual:** A serene, perfect natural snapshot. Leaves gently rustling (looped video).
* **UI:** The final call to action: *"Start classifying today."* with a large, inviting CTA button drawing the user to the web app interface.

## 5. Asset Generation Strategy (AI Pipeline)
* **Visuals / Video:** Use AI video generators (like Sora, Runway Gen-3, or Luma Dream Machine) with prompts like: *"Cinematic drone shot descending through a lush, vibrant green forest canopy, early morning light, anime realism style, 4k, 60fps."*
* **Video Processing:** Extract the generated video into a directory of compressed `.webp` frames using FFmpeg to ensure instant loading on the website.
* **UI Artifacts:** Generate waste item 3D renders with Midjourney or stable-diffusion to use inside the mockups.

## 6. Proposed Tech Stack
* **Framework:** Next.js 14 (App Router)
* **Styling:** Tailwind CSS
* **UI Components:** shadcn/ui
* **Animation:** Framer Motion (for UI entry/exit) + GSAP & Canvas (for background scroll sequencing)
* **Deployment:** Vercel
