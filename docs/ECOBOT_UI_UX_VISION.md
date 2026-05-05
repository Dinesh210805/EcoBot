# EcoBot — UI/UX & Motion Design Architecture

## 1. The Core Vision
**Aesthetic Direction:** *Organic Maximalism meets Industrial Precision.* 
We are moving away from generic "AI startup" templates. Instead of flat white backgrounds and purple gradients, we pull from the lush, breathtaking natural environments of Studio Ghibli and *Vinland Saga*. We contrast these wild, highly detailed, animated natural backgrounds with ultra-crisp, surgical glassmorphic UI panels.

**Tagline Options:**
1. *Nature's Intelligence, Engineered.*
2. *The Earth Remembers. Now You Can Too.*
3. *Classify the Waste. Uncover the Forest.*

## 2. Typography & Color System
**Typography (No generic Inter/Roboto):**
*   **Display / Headings:** *Ogg* or *PP Fragment* — A serif with organic, elegant, sweeping curves that evoke nature and roots, giving a highly editorial, magazine-like feel.
*   **Interface / Body:** *Geist Mono* or *Satoshi* — A highly legible, technical sans-serif for the classification data, stats, and AI chat interface.

**Color Palette System (Semantic & Cinematic):**
*   **Background:** Deep forest shadows (`#0a110a`), morning mist white (`#f4f7f4`).
*   **Surface Cards:** Ultra-frosted glass (`rgba(20, 30, 20, 0.4)`) with strict background-blur (`backdrop-blur-2xl`) and 1px crisp white borders (`rgba(255, 255, 255, 0.1)`).
*   **Accents:** Bioluminescent Green (`#39ff14`), Sunlight Gold (`#ffdf70`), and Alert Red (`#ff3333` for hazardous waste).

## 3. Motion & Technical Architecture
To achieve the "Apple-style" scrollytelling feel without layout thrashing (keeping Core Web Vitals healthy):
*   **Video-to-Canvas Scrubbing:** We will not use standard playing `<video>` tags. Instead, we generate a 60fps cinematic fly-through of a forest, extract it to a `.webp` image sequence, and draw them to an HTML5 `<canvas>`.
*   **GSAP ScrollTrigger:** Binds the canvas frame index to the scrollbar position (frame 1 at the top, frame 300 at the bottom).
*   **Framer Motion:** Handles the physical UI entrances/exits (easing curves: `cubic-bezier(0.16, 1, 0.3, 1)` for fluid, physical momentum).
*   **Hardware Acceleration:** We only animate `transform` and `opacity` properties to ensure 0ms input latency and perfect 60fps scrolling.

## 4. Scene-by-Scene Scroll Journey

### Scene 1: The Descent (Hero)
*   **Visual:** A rich, hyper-detailed anime-realism canopy. Light rays pierce through the leaves.
*   **Motion:** As the user scrolls, the camera physically falls *down* through the branches (canvas scrubbing). 
*   **UI:** The big, elegant *EcoBot* logo (in *Ogg*) scales up and fades to 0% opacity, dissolving into the forest.

### Scene 2: The Discovery (Sticky Section)
*   **Visual:** The camera lands on a highly detailed forest floor. A piece of metallic e-waste is resting on the moss.
*   **Motion:** The scroll locks (pinned section). As the user keeps pushing the scroll wheel, a frosted-glass UI scanner "slides" over the e-waste.
*   **UI:** The scanner highlights the item. A sleek interface slides in dynamically, identifying the item.
    *   *Text:* "E-Waste / Hazardous"
    *   *Action:* The UI seamlessly simulates the EcoBot text/image `/classify` API response in real-time.

### Scene 3: The Global Network (Bento Grid)
*   **Visual:** The background transitions into a beautifully lit macro-shot of water or moss.
*   **UI:** A stunning **Bento Grid** layout elegantly swoops in from different angles featuring staggered entrance delays (30ms per item).
    *   *Grid Item 1:* A real-time counter of items classified.
    *   *Grid Item 2:* A glowing map dotting nearby facilities.
    *   *Grid Item 3:* An interactive microphone button for the voice API.

### Scene 4: The Call to Action (Exit)
*   **Visual:** The camera flies up, out of the forest, revealing a majestic, painted sky.
*   **Motion:** The bento grid scales down out of the viewport.
*   **UI:** A massive, inviting button: *"Initiate Scanner"* with a subtle magnetic cursor hover effect.

## 5. AI Asset Generation Blueprint

We can generate the required assets using modern AI tooling to bypass expensive 3D rendering:

1.  **Background Cinematic Sequences (Runway Gen-3 / Luma Dream Machine):**
    *   *Prompt:* "FPV drone shot descending through a lush, vibrant old-growth forest. Morning cinematic sunlight, volumetric light rays, studio ghibli and vinland saga aesthetic, photorealistic anime style, high detail leaves, slow smooth continuous motion."
2.  **Item Renders (Midjourney v6):**
    *   *Prompt:* "A crushed plastic water bottle resting on vibrant green moss, cinematic lighting, macro photography, extremely detailed, Unreal Engine 5 render style --ar 16:9 --style raw"
3.  **Asset Pipeline script:** 
    *   `ffmpeg -i forest_descent.mp4 -vf scale=1920:-1 -r 30 frames/frame_%04d.webp` (Extracts sequence for the Canvas scroll engine).

## 6. Implementation Checklist
*   [ ] Set up Next.js 14 App Router + Tailwind CSS.
*   [ ] Configure CSS variables matching the Semantic Cinematic Palette.
*   [ ] Implement GSAP `ScrollTrigger` and HTML `<canvas>` frame drawing logic.
*   [ ] Build the Glassmorphic base components utilizing `shadcn/ui` combined with `framer-motion` for shared layout animations.
*   [ ] Add `lenis` or `@studio-freight/react-lenis` for buttery smooth scrolling mechanics.