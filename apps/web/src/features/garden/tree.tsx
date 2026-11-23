"use client";

import Image from "next/image";
import { spriteSrc, type Species } from "./species";

/** One growth stage of a species. Sprites are small webp files already sized for the screen: no image optimizer needed. */
export function TreeSprite({ species, stage, size = 160, alt, className, priority }: {
  species: Species;
  stage: number;
  size?: number;
  alt?: string;
  className?: string;
  priority?: boolean;
}) {
  return (
    <Image
      src={spriteSrc(species.id, stage)}
      width={size}
      height={size}
      alt={alt ?? `${species.name}: ${species.stages[stage] ?? ""}`}
      className={`tree-sprite${className ? ` ${className}` : ""}`}
      unoptimized
      priority={priority}
      draggable={false}
    />
  );
}

/** Round mascot face for chat bubbles and buttons: the species at its current stage, tinted ring in its color. */
export function MascotAvatar({ species, stage, size = 36, className }: { species: Species; stage: number; size?: number; className?: string }) {
  return (
    <span
      className={`mascot-avatar${className ? ` ${className}` : ""}`}
      style={{ width: size, height: size, ["--mascot" as string]: species.accent }}
      aria-hidden="true"
    >
      <TreeSprite species={species} stage={stage} size={size} alt="" />
    </span>
  );
}
