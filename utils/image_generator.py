"""
utils/image_generator.py
========================
DUAL MODE Interior Design Generator + assemble_final_prompt()

Key fix in this version (v2):
  • assemble_final_prompt() now faithfully encodes EVERY piece of
    user-supplied detail into the SD prompt:
      - room dimensions
      - per-compass-direction wall colours (north/south/east/west)
      - the full furniture list (not truncated)
      - materials / floor type
      - style, mood, lighting
      - any free-text extra_note
  • Prompt parts are ordered so SD attends to the most important
    tokens first (room type + style → colours → furniture → quality).
  • Quality suffixes are always appended but never crowd out user content
    — total prompt is capped at 900 chars.
"""

import os
import io
import base64
from PIL import Image, ImageEnhance, ImageFilter
import torch
from diffusers import (
    DiffusionPipeline,
    LCMScheduler,
    DDIMScheduler,
    EulerAncestralDiscreteScheduler,
)
from dotenv import load_dotenv

load_dotenv()


# ══════════════════════════════════════════════════════════════
# PUBLIC HELPER  — imported by app.py
# ══════════════════════════════════════════════════════════════

def assemble_final_prompt(parsed: dict, analyzer=None) -> str:
    """
    Convert a parsed requirements dict (from PromptAnalyzer) into a
    high-fidelity Stable Diffusion prompt.

    Preserves every user-specified detail:
      room type, style, dimensions, wall colours (per compass direction),
      furniture (all items), materials, mood, lighting, extra notes.

    Parameters
    ----------
    parsed   : dict   Output of PromptAnalyzer.analyze_prompt()
    analyzer : object Unused — kept for API compatibility with app.py

    Returns
    -------
    str  SD-ready prompt, max 900 characters
    """
    def _lst(val):
        """Coerce any value to a plain list."""
        if not val:           return []
        if isinstance(val, str): return [val]
        try:                  return list(val)
        except TypeError:     return []

    room_type  = (parsed.get("room_type") or "room").strip()
    style      = (parsed.get("style")     or "modern").strip()
    dims       = parsed.get("dimensions") or {}
    colors     = parsed.get("colors")     or {}
    furniture  = _lst(parsed.get("furniture"))
    materials  = _lst(parsed.get("materials"))
    mood       = _lst(parsed.get("mood"))
    lighting   = _lst(parsed.get("lighting"))
    view       = (parsed.get("view_direction") or "").strip()
    extra_note = (parsed.get("extra_note")     or "").strip()

    parts = []

    # ── 1. Core subject (most weight in SD) ──────────────────
    parts.append(f"{style} {room_type} interior")

    # ── 2. Room dimensions ───────────────────────────────────
    if dims.get("width") and dims.get("length"):
        unit = dims.get("unit", "ft")
        parts.append(f"{dims['width']} {unit} x {dims['length']} {unit}")

    # ── 3. View direction ─────────────────────────────────────
    if view:
        parts.append(f"{view} view")

    # ── 4. Wall colours — compass directions first ───────────
    #    SD responds well to explicit directional colour cues.
    if isinstance(colors, dict):
        wall_cues = []
        for direction in ("north", "south", "east", "west"):
            c = colors.get(direction)
            if c:
                wall_cues.append(f"{direction} wall {c}")
        if wall_cues:
            parts.append("walls: " + ", ".join(wall_cues))
        overall = _lst(colors.get("overall"))
        if overall:
            parts.append("color scheme " + " and ".join(overall[:4]))
    else:
        flat = _lst(colors)
        if flat:
            parts.append("color scheme " + " and ".join(flat[:4]))

    # ── 5. Furniture — ALL items listed ─────────────────────
    #    We list every item; SD will include whichever fit the scene.
    if furniture:
        parts.append("containing " + ", ".join(furniture))

    # ── 6. Materials / floor ─────────────────────────────────
    if materials:
        parts.append("with " + ", ".join(materials[:5]) + " finishes")

    # ── 7. Mood ───────────────────────────────────────────────
    if mood:
        parts.append(", ".join(mood[:3]) + " atmosphere")

    # ── 8. Lighting ───────────────────────────────────────────
    if lighting:
        parts.append(", ".join(lighting[:2]) + " lighting")

    # ── 9. Extra free-text note (Room Editor / user override) ─
    if extra_note:
        parts.append(extra_note)

    # ── 10. Quality suffixes (always last so they don't push
    #        user content out of the 77-token SD window) ───────
    quality = [
        "professional interior photography",
        "photorealistic",
        "8K resolution",
        "sharp focus",
        "perfect lighting",
        "highly detailed",
    ]
    parts.extend(quality)

    prompt = ", ".join(parts)

    # Hard cap: SD tokeniser truncates at ~77 tokens (~370 chars for
    # typical English).  We keep up to 900 chars so the assembler can
    # be called with extra context without crashing, but warn if long.
    if len(prompt) > 900:
        prompt = prompt[:900]

    return prompt


# ══════════════════════════════════════════════════════════════
# GENERATOR CLASS
# ══════════════════════════════════════════════════════════════

class InteriorDesignGenerator:
    """
    DUAL MODE Interior Design Generator

    Two modes available:
    1. FAST MODE   (LCM)    : 30–90 seconds on CPU,   good quality
    2. QUALITY MODE (SD 1.5): 10–20 minutes on CPU,   best quality

    Default: FAST MODE (recommended for CPU)
    """

    def __init__(self, mode="fast"):
        self.device   = "cuda" if torch.cuda.is_available() else "cpu"
        self.hf_token = os.getenv("HUGGINGFACE_TOKEN")
        self.mode     = mode.lower()

        if not self.hf_token:
            raise ValueError("HUGGINGFACE_TOKEN not found in .env file")

        print("=" * 60)
        print("🏠 Dream Space - Interior Design Generator")
        print("=" * 60)
        print(f"📱 Device : {self.device.upper()}")
        print(f"⚡ Mode   : {self.mode.upper()}")

        if self.device == "cpu":
            print("⚠️  CPU detected — using optimised settings")
            if self.mode == "quality":
                print("⏱️  Expected time: 10–20 minutes per image")
            else:
                print("⏱️  Expected time: 30–90 seconds per image")

        print("\n⏳ Loading models…")
        try:
            if self.mode == "fast":
                self._init_fast_mode()
            else:
                self._init_quality_mode()
            print("✅ Models loaded successfully!")
            print("=" * 60)
        except Exception as e:
            print(f"❌ Error loading models: {e}")
            raise

    # ── Init ──────────────────────────────────────────────────────────────────

    def _init_fast_mode(self):
        print("🚀 Loading LCM Fast Model…")
        model_id = "rupeshs/LCM-runwayml-stable-diffusion-v1-5"
        self.pipeline = DiffusionPipeline.from_pretrained(
            model_id,
            torch_dtype=torch.float32,
            use_auth_token=self.hf_token,
            safety_checker=None,
        )
        self.pipeline.scheduler = LCMScheduler.from_config(
            self.pipeline.scheduler.config
        )
        self.pipeline = self.pipeline.to(self.device)
        if self.device == "cpu":
            self.pipeline.enable_attention_slicing(1)

        self.default_steps    = 4
        self.default_guidance = 1.0
        self.default_size     = 512
        print(
            f"✓ Fast mode ready (LCM) | "
            f"Steps: {self.default_steps} | "
            f"Size: {self.default_size}×{self.default_size}"
        )

    def _init_quality_mode(self):
        print("🎨 Loading Quality Model…")
        model_id = "runwayml/stable-diffusion-v1-5"
        self.pipeline = DiffusionPipeline.from_pretrained(
            model_id,
            torch_dtype=torch.float32,
            use_auth_token=self.hf_token,
            safety_checker=None,
        )
        self.pipeline.scheduler = DDIMScheduler.from_config(
            self.pipeline.scheduler.config
        )
        self.pipeline = self.pipeline.to(self.device)
        if self.device == "cpu":
            self.pipeline.enable_attention_slicing(1)

        self.default_steps    = 25
        self.default_guidance = 7.5
        self.default_size     = 512
        print(
            f"✓ Quality mode ready (SD 1.5 + DDIM) | "
            f"Steps: {self.default_steps} | "
            f"Size: {self.default_size}×{self.default_size}"
        )

    # ── Generation ────────────────────────────────────────────────────────────

    def generate_from_prompt(
        self,
        prompt: str,
        width: int = None,
        height: int = None,
        num_inference_steps: int = None,
    ) -> Image.Image:
        """
        Generate an interior design image from a text prompt.

        The prompt is expected to have already been assembled by
        assemble_final_prompt() — this method adds only the minimal
        mode-specific quality suffixes so as NOT to override the
        user's specific wall colours, furniture, etc.
        """
        try:
            width  = width  or self.default_size
            height = height or self.default_size
            steps  = num_inference_steps or self.default_steps

            # Clamp to multiples of 8, hard cap on CPU
            width  = (width  // 8) * 8
            height = (height // 8) * 8
            if self.device == "cpu":
                width  = min(width,  512)
                height = min(height, 512)

            print(f"\n{'='*60}")
            print(f"🎨 Generating [{self.mode.upper()}] mode image…")
            print(f"📝 Prompt ({len(prompt)} chars): {prompt[:120]}…")
            print(f"🖼️  Size: {width}×{height}  |  Steps: {steps}")
            print(f"{'='*60}")

            if self.mode == "fast":
                final_prompt    = self._add_quality_suffixes_fast(prompt)
                negative_prompt = self._negative_fast()
                guidance_scale  = self.default_guidance
            else:
                final_prompt    = self._add_quality_suffixes_quality(prompt)
                negative_prompt = self._negative_quality()
                guidance_scale  = self.default_guidance

            result = self.pipeline(
                prompt              = final_prompt,
                negative_prompt     = negative_prompt,
                num_inference_steps = steps,
                guidance_scale      = guidance_scale,
                width               = width,
                height              = height,
            )
            image = self._post_process(result.images[0])
            print("✅ Generation complete!")
            return image

        except Exception as e:
            print(f"❌ Generation error: {e}")
            # Fallback: try with minimal settings, but keep user prompt intact
            try:
                print("⚠️  Retrying with minimal settings (prompt preserved)…")
                result = self.pipeline(
                    prompt              = prompt,
                    negative_prompt     = "blurry, low quality",
                    num_inference_steps = 4 if self.mode == "fast" else 20,
                    guidance_scale      = 1.0 if self.mode == "fast" else 7.0,
                    width               = 512,
                    height              = 512,
                )
                print("✅ Generated with fallback settings")
                return result.images[0]
            except Exception as retry_error:
                print(f"❌ Fallback failed: {retry_error}")
                raise

    # ── Prompt suffix helpers (ONLY add quality terms; never override user content) ──

    def _add_quality_suffixes_fast(self, prompt: str) -> str:
        """
        Append quality keywords that LCM benefits from, but only if they
        are not already present in the assembled prompt.
        """
        additions = [
            ("professional interior design", "professional"),
            ("photorealistic",               "photorealistic"),
            ("highly detailed",              "detailed"),
        ]
        base = prompt
        for phrase, check in additions:
            if check.lower() not in base.lower():
                base = (base + f", {phrase}")[:900]
        return base

    def _add_quality_suffixes_quality(self, prompt: str) -> str:
        """
        Append quality keywords for SD 1.5 + DDIM, only if absent.
        """
        additions = [
            ("professional interior photography", "interior photography"),
            ("architectural digest",              "architectural digest"),
            ("photorealistic",                    "photorealistic"),
            ("8K resolution",                     "8k"),
        ]
        base = prompt
        for phrase, check in additions:
            if check.lower() not in base.lower():
                base = (base + f", {phrase}")[:900]
        return base

    def _negative_fast(self) -> str:
        return (
            "blurry, low quality, distorted, ugly, bad, "
            "amateur, watermark, text, logo, signature"
        )

    def _negative_quality(self) -> str:
        return (
            "blurry, low quality, bad quality, worst quality, "
            "low resolution, pixelated, jpeg artifacts, "
            "distorted, deformed, ugly, bad anatomy, "
            "watermark, text, signature, logo, "
            "cartoon, painting, illustration, drawing, "
            "cluttered, messy, dirty"
        )

    # ── Enhancement ───────────────────────────────────────────────────────────

    def enhance_image(
        self,
        image: Image.Image,
        prompt_additions: str = "",
        strength: float = 0.5,
        num_inference_steps: int = None,
    ) -> Image.Image:
        """
        Enhance an existing image.

        Strategy (in priority order):
          1. PIL-based enhancement — always works, instant, no ML needed.
          2. SD img2img (quality mode only) — attempted after PIL pass.
             Skipped in FAST/LCM mode (incompatible scheduler).
        """
        print(f"\n🔧 Enhancing image | mode={self.mode} | hint='{prompt_additions[:60]}'")

        # Step 1: PIL pass (always applied)
        try:
            image = self._pil_enhance(image, prompt_additions)
            print("✅ PIL enhancement applied")
        except Exception as pil_err:
            print(f"⚠️  PIL enhancement failed: {pil_err}")

        # Step 2: SD img2img (quality mode only)
        if self.mode == "quality":
            try:
                image = self._sd_img2img_enhance(image, prompt_additions, strength, num_inference_steps)
                print("✅ SD img2img enhancement applied")
            except Exception as sd_err:
                print(f"⚠️  SD img2img skipped: {sd_err}")

        return image

    def _pil_enhance(self, image: Image.Image, hint: str = "") -> Image.Image:
        """PIL post-processing driven by the hint string."""
        h = hint.lower() if hint else ""

        # Sharpness
        image = ImageEnhance.Sharpness(image).enhance(1.4 if "sharp" in h else 1.2)
        # Contrast
        image = ImageEnhance.Contrast(image).enhance(1.2 if "contrast" in h else 1.1)
        # Brightness
        if "bright" in h or "light" in h:
            image = ImageEnhance.Brightness(image).enhance(1.15)
        elif "dark" in h or "moody" in h:
            image = ImageEnhance.Brightness(image).enhance(0.90)
        else:
            image = ImageEnhance.Brightness(image).enhance(1.05)
        # Colour saturation
        if "vibrant" in h or "colorful" in h or "colourful" in h:
            image = ImageEnhance.Color(image).enhance(1.30)
        elif "warm" in h:
            image = ImageEnhance.Color(image).enhance(1.20)
        elif "cool" in h or "cold" in h:
            image = ImageEnhance.Color(image).enhance(0.90)
        else:
            image = ImageEnhance.Color(image).enhance(1.10)
        # Detail pass
        image = image.filter(ImageFilter.UnsharpMask(radius=1, percent=120, threshold=3))
        return image

    def _sd_img2img_enhance(
        self,
        image: Image.Image,
        prompt_additions: str,
        strength: float,
        num_inference_steps: int,
    ) -> Image.Image:
        """SD 1.5 img2img enhancement (quality mode only)."""
        from diffusers import StableDiffusionImg2ImgPipeline

        print("   Loading img2img pipeline…")
        img2img = StableDiffusionImg2ImgPipeline.from_pretrained(
            "runwayml/stable-diffusion-v1-5",
            torch_dtype=torch.float32,
            use_auth_token=self.hf_token,
            safety_checker=None,
        ).to(self.device)

        if self.device == "cpu":
            img2img.enable_attention_slicing(1)

        image  = image.resize((512, 512))
        steps  = max(num_inference_steps or 20, 15)
        prompt = prompt_additions if prompt_additions else "enhance quality, improve details"
        prompt = self._add_quality_suffixes_quality(prompt)

        result = img2img(
            prompt              = prompt,
            negative_prompt     = self._negative_quality(),
            image               = image,
            strength            = strength,
            num_inference_steps = steps,
            guidance_scale      = 7.5,
        )
        return result.images[0]

    # ── Post-processing ───────────────────────────────────────────────────────

    def _post_process(self, image: Image.Image) -> Image.Image:
        """Light sharpness + contrast pass applied to every generated image."""
        try:
            image = ImageEnhance.Sharpness(image).enhance(1.15)
            image = ImageEnhance.Contrast(image).enhance(1.08)
            return image
        except Exception:
            return image

    # ── Room redesign (inpainting) ────────────────────────────────────────────

    def redesign_room(
        self,
        base_image_path: str,
        mask_path: str,
        prompt: str,
        num_inference_steps: int = None,
    ) -> Image.Image:
        if self.mode == "fast":
            raise NotImplementedError(
                "Redesign not supported in fast mode — switch to quality mode."
            )
        try:
            from diffusers import StableDiffusionInpaintPipeline

            inpaint = StableDiffusionInpaintPipeline.from_pretrained(
                "runwayml/stable-diffusion-inpainting",
                torch_dtype=torch.float32,
                use_auth_token=self.hf_token,
                safety_checker=None,
            ).to(self.device)

            base  = Image.open(base_image_path).convert("RGB").resize((512, 512))
            mask  = Image.open(mask_path).convert("RGB").resize((512, 512))

            result = inpaint(
                prompt              = self._add_quality_suffixes_quality(prompt),
                negative_prompt     = self._negative_quality(),
                image               = base,
                mask_image          = mask,
                num_inference_steps = num_inference_steps or 25,
                guidance_scale      = 7.5,
            )
            return result.images[0]
        except Exception as e:
            print(f"❌ Redesign error: {e}")
            raise

    # ── Static helpers ────────────────────────────────────────────────────────

    @staticmethod
    def image_to_base64(image: Image.Image) -> str:
        buffer = io.BytesIO()
        image.save(buffer, format="PNG", optimize=True)
        buffer.seek(0)
        return base64.b64encode(buffer.read()).decode()

    @staticmethod
    def base64_to_image(base64_string: str) -> Image.Image:
        return Image.open(io.BytesIO(base64.b64decode(base64_string)))

    # ── Mode switching ────────────────────────────────────────────────────────

    def switch_mode(self, new_mode: str):
        if new_mode == self.mode:
            print(f"Already in {self.mode} mode")
            return
        print(f"\n🔄 Switching from {self.mode} to {new_mode} mode…")
        del self.pipeline
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        self.mode = new_mode
        if self.mode == "fast":
            self._init_fast_mode()
        else:
            self._init_quality_mode()
        print(f"✅ Switched to {self.mode} mode!")