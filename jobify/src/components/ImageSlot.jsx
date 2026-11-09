import React, { useState } from "react";
import { IMAGE_SLOTS } from "../data/images.js";
import { cn } from "../lib/utils.js";

/**
 * ImageSlot component with responsive sizing, intrinsic aspect-ratio reservation,
 * and aesthetic fallback gradients matching the misty green mountain aesthetic.
 */
export default function ImageSlot({
  slotKey,
  className = "",
  style = {},
  loading = "lazy",
  fetchPriority = "auto",
  objectPosition = "center",
  customAlt,
  customSrc,
  children,
}) {
  const meta = IMAGE_SLOTS[slotKey] || {
    src: customSrc || "",
    alt: customAlt || "",
    ariaHidden: true,
    width: 1200,
    height: 800,
  };

  const src = customSrc || meta.src;
  const alt = customAlt !== undefined ? customAlt : meta.alt;
  const ariaHidden = meta.ariaHidden && !customAlt;

  const [hasError, setHasError] = useState(false);
  const [isLoaded, setIsLoaded] = useState(false);

  // Fallback visual representations
  const renderVisualFallback = () => {
    switch (slotKey) {
      case "hero-landscape":
      case "footer-landscape":
        return (
          <div
            className="w-full h-full relative overflow-hidden"
            style={{
              background:
                "linear-gradient(180deg, #F9FAF8 0%, #E3EFE3 20%, #B8D6B8 50%, #6E9B6E 80%, #466C47 100%)",
            }}
          >
            {/* Mountain Ridgelines SVG */}
            <svg
              className="absolute inset-0 w-full h-full opacity-85"
              viewBox="0 0 1440 600"
              preserveAspectRatio="xMidYMax slice"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
              aria-hidden="true"
            >
              <path
                d="M-50 420 C 180 340, 360 410, 620 330 C 890 250, 1150 360, 1500 290 L 1500 650 L -50 650 Z"
                fill="#8BAF88"
                opacity="0.45"
              />
              <path
                d="M-40 450 C 220 380, 480 430, 740 370 C 1020 310, 1260 410, 1500 360 L 1500 650 L -40 650 Z"
                fill="#6A9468"
                opacity="0.6"
              />
              <path
                d="M-20 490 C 260 440, 560 480, 860 430 C 1140 380, 1340 470, 1480 440 L 1480 650 L -20 650 Z"
                fill="#4D774A"
                opacity="0.8"
              />
              <path
                d="M0 540 C 240 490, 520 540, 820 500 C 1120 460, 1320 530, 1440 510 L 1440 650 L 0 650 Z"
                fill="#3B6338"
              />
            </svg>
            <div className="absolute inset-0 bg-gradient-to-t from-white/20 via-transparent to-white/60 pointer-events-none" />
          </div>
        );

      case "hero-portrait":
        return (
          <div className="w-full h-full relative flex items-end justify-center overflow-hidden">
            {/* Elegant high-contrast portrait illustration */}
            <svg
              viewBox="0 0 450 550"
              className="w-full h-auto max-h-full object-contain filter contrast-125"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
              aria-hidden="true"
            >
              <defs>
                <linearGradient id="torsoFade" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#111111" />
                  <stop offset="70%" stopColor="#1A1A1A" />
                  <stop offset="100%" stopColor="#1A1A1A" stopOpacity="0" />
                </linearGradient>
                <radialGradient id="faceShade" cx="45%" cy="35%" r="60%">
                  <stop offset="0%" stopColor="#EAEAEA" />
                  <stop offset="60%" stopColor="#B3B3B3" />
                  <stop offset="100%" stopColor="#555555" />
                </radialGradient>
              </defs>
              {/* Torso & high collar silhouette */}
              <path
                d="M130 550 C 130 460, 180 430, 215 390 C 225 350, 228 320, 230 300 C 245 305, 275 305, 290 300 C 295 330, 310 420, 370 550 Z"
                fill="url(#torsoFade)"
              />
              {/* Neck */}
              <path
                d="M218 310 C 218 260, 222 230, 226 210 C 248 214, 274 212, 282 208 C 286 230, 288 270, 286 310 Z"
                fill="url(#faceShade)"
              />
              {/* Jawline & Profile */}
              <path
                d="M225 210 C 220 185, 216 165, 206 155 C 200 150, 190 148, 185 142 C 178 135, 184 125, 192 120 C 185 110, 180 95, 188 85 C 196 75, 212 70, 225 70 C 240 60, 270 55, 305 75 C 330 92, 340 120, 335 150 C 330 180, 305 210, 282 208 Z"
                fill="url(#faceShade)"
              />
              {/* Textured pixie cut hair in deep black */}
              <path
                d="M188 85 C 180 70, 200 50, 235 45 C 275 40, 320 50, 345 85 C 360 110, 355 145, 340 170 C 330 150, 325 125, 310 110 C 290 95, 260 90, 235 98 C 210 105, 198 120, 185 142 C 180 120, 182 100, 188 85 Z"
                fill="#0A0A0A"
              />
              {/* Closed eyelid / calm facial contour */}
              <path
                d="M200 126 C 206 130, 215 130, 222 125"
                stroke="#444444"
                strokeWidth="2.5"
                strokeLinecap="round"
              />
              <path
                d="M190 146 C 198 147, 208 147, 214 144"
                stroke="#666666"
                strokeWidth="2"
                strokeLinecap="round"
              />
            </svg>
          </div>
        );

      case "feature-automation-bg":
        return (
          <div
            className="w-full h-full relative"
            style={{
              background:
                "linear-gradient(135deg, #DEEDE1 0%, #AECDAF 40%, #769E76 75%, #4C724C 100%)",
            }}
          >
            <div className="absolute inset-0 bg-radial from-transparent to-black/15" />
          </div>
        );

      case "feature-analytics-bg":
        return (
          <div
            className="w-full h-full relative"
            style={{
              background:
                "linear-gradient(145deg, #E6F2E8 0%, #BDDCBF 35%, #88AF85 70%, #578054 100%)",
            }}
          >
            <div className="absolute inset-0 bg-gradient-to-t from-black/20 via-transparent to-white/30" />
          </div>
        );

      case "benefits-bg":
        return (
          <div
            className="w-full h-full relative overflow-hidden"
            style={{
              background:
                "linear-gradient(180deg, #BFD9F0 0%, #DCECF8 45%, #E3EFE3 70%, #6E9B6E 100%)",
            }}
          >
            {/* Rock outcroppings & meadow ridge */}
            <svg
              className="absolute bottom-0 inset-x-0 w-full h-48 opacity-90"
              viewBox="0 0 1200 200"
              preserveAspectRatio="none"
              fill="none"
            >
              <path
                d="M0 120 Q 300 90, 600 130 T 1200 100 L 1200 200 L 0 200 Z"
                fill="#5B8359"
              />
              <path
                d="M-20 150 Q 400 110, 800 160 T 1220 130 L 1220 200 L -20 200 Z"
                fill="#466C47"
              />
              {/* Rock formations left and right */}
              <path
                d="M0 140 L 90 90 L 170 170 L 0 200 Z"
                fill="#9EA89E"
                opacity="0.85"
              />
              <path
                d="M1030 160 L 1120 85 L 1200 140 L 1200 200 L 1030 200 Z"
                fill="#949E94"
                opacity="0.85"
              />
            </svg>
          </div>
        );

      case "integration-bg":
        return (
          <div
            className="w-full h-full relative"
            style={{
              background:
                "linear-gradient(180deg, #CEE5F6 0%, #E3F1FB 40%, #A8CD9B 75%, #649658 100%)",
            }}
          >
            <div className="absolute inset-0 bg-gradient-to-t from-black/15 to-transparent" />
          </div>
        );

      case "usecase-marketing":
        return (
          <div
            className="w-full h-full relative"
            style={{
              background:
                "linear-gradient(180deg, #99C5E8 0%, #D0E5F5 35%, #768F9E 55%, #4C724C 75%, #2B4B2A 100%)",
            }}
          >
            {/* Mountain peak impression */}
            <svg
              className="absolute inset-0 w-full h-full opacity-60"
              viewBox="0 0 400 500"
              preserveAspectRatio="none"
            >
              <polygon
                points="120,240 220,110 320,270"
                fill="#EAEFF2"
                opacity="0.8"
              />
              <polygon
                points="220,110 240,150 210,170"
                fill="#FFFFFF"
              />
              <polygon
                points="50,330 200,210 350,340"
                fill="#4E6B50"
                opacity="0.9"
              />
            </svg>
          </div>
        );

      case "avatar-1":
      case "avatar-2":
      case "avatar-3": {
        const tints = {
          "avatar-1": "#E6EDE3",
          "avatar-2": "#E8ECEF",
          "avatar-3": "#EDE8E4",
        };
        const accents = {
          "avatar-1": "#466C47",
          "avatar-2": "#5B7BD5",
          "avatar-3": "#D97706",
        };
        return (
          <div
            className="w-full h-full flex items-center justify-center rounded-full text-xs font-semibold"
            style={{
              backgroundColor: tints[slotKey] || "#EEEEEE",
              color: accents[slotKey] || "#333333",
            }}
          >
            <svg
              viewBox="0 0 24 24"
              className="w-6 h-6 opacity-75"
              fill="currentColor"
            >
              <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z" />
            </svg>
          </div>
        );
      }

      default:
        return (
          <div className="w-full h-full bg-gradient-to-br from-[#E3EFE3] via-[#B8D6B8] to-[#6E9B6E]" />
        );
    }
  };

  return (
    <div
      className={cn("relative overflow-hidden", className)}
      style={{
        aspectRatio: meta.aspectRatio || "auto",
        ...style,
      }}
    >
      {/* If error or not loaded, show aesthetic styled CSS/SVG fallback */}
      {(!isLoaded || hasError) && (
        <div className="absolute inset-0 w-full h-full z-0 transition-opacity duration-300">
          {renderVisualFallback()}
        </div>
      )}

      {/* Actual <img> tag trying local or custom src */}
      {src && !hasError && (
        <img
          src={src}
          alt={alt}
          width={meta.width}
          height={meta.height}
          loading={loading}
          fetchPriority={fetchPriority}
          decoding="async"
          onLoad={() => setIsLoaded(true)}
          onError={() => setHasError(true)}
          className={cn(
            "relative z-10 w-full h-full object-cover transition-opacity duration-500",
            isLoaded ? "opacity-100" : "opacity-0"
          )}
          style={{ objectPosition }}
          aria-hidden={ariaHidden}
        />
      )}

      {children}
    </div>
  );
}
