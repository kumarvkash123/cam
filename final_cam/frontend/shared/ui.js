"use client";

import React from "react";

function BOBMark({ small = false }) {
  return (
    <div className={`bob-mark ${small ? "small" : ""}`}>
      B
    </div>
  );
}

function Icon({ name }) {
  const paths = {
    home: (
      <>
        <path d="M3 10.5 12 3l9 7.5" />
        <path d="M5.5 9.5V21h13V9.5" />
        <path d="M9.5 21v-6h5v6" />
      </>
    ),

    file: (
      <>
        <path d="M6 2.8h8l4 4V21H6z" />
        <path d="M14 2.8V7h4" />
        <path d="M9 11h6M9 15h6" />
      </>
    ),

    users: (
      <>
        <circle cx="9" cy="8" r="3" />
        <path d="M3.5 20c.5-3.2 2.3-5 5.5-5s5 1.8 5.5 5" />
        <path d="M16 5.5a3 3 0 0 1 0 5.5M17 15c2.4.5 3.5 2 3.8 4" />
      </>
    ),

    building: (
      <>
        <path d="M4 21V6l8-3 8 3v15" />
        <path d="M2 21h20M8 9h2M14 9h2M8 13h2M14 13h2M8 17h2M14 17h2" />
      </>
    ),

    chart: (
      <>
        <path d="M4 19V5M4 19h17" />
        <path d="m7 15 4-5 3 2 5-7" />
      </>
    ),

    shield: (
      <>
        <path d="M12 3 20 6v6c0 5-3.4 8.4-8 10-4.6-1.6-8-5-8-10V6z" />
        <path d="m8.5 12 2.2 2.2 4.8-5" />
      </>
    ),

    spark: (
      <>
        <path d="m12 3 1.5 5.5L19 10l-5.5 1.5L12 17l-1.5-5.5L5 10l5.5-1.5z" />
        <path d="m19 16 .7 2.3L22 19l-2.3.7L19 22l-.7-2.3L16 19l2.3-.7z" />
      </>
    ),

    bell: (
      <>
        <path d="M18 9a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9" />
        <path d="M10 21h4" />
      </>
    ),

    settings: (
      <>
        <circle cx="12" cy="12" r="3" />
        <path d="M19.4 15a1.8 1.8 0 0 0 .3 2l.1.1-1.8 1.8-.1-.1a1.8 1.8 0 0 0-2-.3 1.8 1.8 0 0 0-1.1 1.7V20h-2.6v-.2a1.8 1.8 0 0 0-1.1-1.7 1.8 1.8 0 0 0-2 .3l-.1.1-1.8-1.8.1-.1a1.8 1.8 0 0 0 .3-2A1.8 1.8 0 0 0 6 13.8H5.8v-2.6H6a1.8 1.8 0 0 0 1.6-1.1 1.8 1.8 0 0 0-.3-2l-.1-.1L9 6.2l.1.1a1.8 1.8 0 0 0 2 .3 1.8 1.8 0 0 0 1.1-1.7V4h2.6v.2a1.8 1.8 0 0 0 1.1 1.7 1.8 1.8 0 0 0 2-.3l.1-.1 1.8 1.8-.1.1a1.8 1.8 0 0 0-.3 2 1.8 1.8 0 0 0 1.7 1.1h.2v2.6H21a1.8 1.8 0 0 0-1.6 1.1Z" />
      </>
    ),

    search: (
      <>
        <circle cx="10.8" cy="10.8" r="6.8" />
        <path d="m16 16 5 5" />
      </>
    ),

    menu: (
      <>
        <path d="M4 7h16M4 12h16M4 17h16" />
      </>
    ),

    logout: (
      <>
        <path d="M10 4H5v16h5M14 8l4 4-4 4M18 12H9" />
      </>
    ),

    arrow: (
      <>
        <path d="M5 12h14M13 6l6 6-6 6" />
      </>
    ),

    clock: (
      <>
        <circle cx="12" cy="12" r="9" />
        <path d="M12 7v5l3 2" />
      </>
    ),

    upload: (
      <>
        <path d="M12 16V4M7 9l5-5 5 5" />
        <path d="M5 15v5h14v-5" />
      </>
    ),
  };

  return (
    <svg
      className="ui-icon"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {paths[name] || paths.file}
    </svg>
  );
}


/* -------------------------------------------------------
   Common formatting helpers
------------------------------------------------------- */

function humanize(value) {
  if (value === null || value === undefined) {
    return "";
  }

  return String(value)
    .replace(/[_-]+/g, " ")
    .replace(/([a-z])([A-Z])/g, "$1 $2")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/\b\w/g, (char) => char.toUpperCase());
}


function formatValue(value) {
  if (value === null || value === undefined || value === "") {
    return "Not available";
  }

  if (Array.isArray(value)) {
    if (value.length === 0) {
      return "Not available";
    }

    return value
      .map((item) => {
        if (typeof item === "object" && item !== null) {
          return JSON.stringify(item);
        }

        return String(item);
      })
      .join(", ");
  }

  if (typeof value === "object") {
    return Object.entries(value)
      .map(([key, val]) => `${humanize(key)}: ${formatValue(val)}`)
      .join(" | ");
  }

  if (typeof value === "boolean") {
    return value ? "Yes" : "No";
  }

  return String(value);
}


/* -------------------------------------------------------
   Assistant response rendering
------------------------------------------------------- */

function InlineText({ text }) {
  const parts = String(text || "").split(/(\*\*[^*]+\*\*)/g);

  return (
    <>
      {parts.map((part, index) => {
        if (
          part.startsWith("**") &&
          part.endsWith("**")
        ) {
          return (
            <strong key={index}>
              {part.slice(2, -2)}
            </strong>
          );
        }

        return part;
      })}
    </>
  );
}


function AssistantText({ text }) {
  const raw = String(text || "").replace(/\r/g, "");

  const lines = raw.split("\n");

  return (
    <div className="assistant-text">
      {lines.map((line, index) => {
        const s = line.trim();

        if (!s) {
          return (
            <div
              key={index}
              className="assistant-spacer"
            />
          );
        }

        // Markdown heading
        if (/^#{1,4}\s+/.test(s)) {
          return (
            <h4 key={index}>
              {s.replace(/^#{1,4}\s+/, "")}
            </h4>
          );
        }

        // Bullet
        if (/^[-*•]\s+/.test(s)) {
          return (
            <div
              key={index}
              className="assistant-bullet"
            >
              •{" "}
              <InlineText
                text={s.replace(/^[-*•]\s+/, "")}
              />
            </div>
          );
        }

        // Numbered list
        if (/^\d+[.)]\s+/.test(s)) {
          return (
            <div
              key={index}
              className="assistant-number"
            >
              <InlineText text={s} />
            </div>
          );
        }

        // Long plain assistant paragraphs are rendered as readable bullets.
        if (s.length >= 220) {
          const protectedText = s.replace(/\b(Pvt|Ltd|Mr|Mrs|Ms|Dr|Prof|No|Cr)\./g, "$1§");
          const sentences = protectedText.split(/(?<=[.!?])\s+(?=[A-Z0-9₹])/).filter(Boolean).map((x) => x.replace(/§/g, "."));
          if (sentences.length >= 3) {
            return (
              <div key={index} className="assistant-auto-bullets">
                {sentences.map((sentence, j) => (
                  <div key={j} className="assistant-bullet">• <InlineText text={sentence.trim()} /></div>
                ))}
              </div>
            );
          }
        }

        // Normal paragraph
        return (
          <p key={index}>
            <InlineText text={s} />
          </p>
        );
      })}
    </div>
  );
}


export {
  BOBMark,
  Icon,
  humanize,
  formatValue,
  AssistantText,
};