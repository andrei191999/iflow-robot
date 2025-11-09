import React from "react";

export default function Toggle({
  checked,
  onChange,
}: {
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <button
      type="button"
      onClick={() => onChange(!checked)}
      className={`h-6 w-11 rounded-full transition-colors ${
        checked ? "bg-brand-500" : "bg-gray-300"
      }`}
    >
      <span
        className={`block h-5 w-5 rounded-full bg-white m-0.5 transition-transform ${
          checked ? "translate-x-5" : ""
        }`}
      />
    </button>
  );
}
