import React, { useEffect } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft } from "lucide-react";

/**
 * On-brand placeholder page for registered sub-routes in Jobify.
 */
export default function StubPage({ title, description }) {
  useEffect(() => {
    document.title = `${title} | Jobify`;
    window.scrollTo(0, 0);
  }, [title]);

  return (
    <main
      id="main-content"
      className="min-h-[60vh] flex items-center justify-center py-20 px-6 sm:px-8 bg-white"
    >
      <div className="max-w-[560px] w-full text-center flex flex-col items-center">
        <span className="inline-block px-3 py-1 rounded-full bg-[#F7F7F7] border border-[#E8E8E8] text-[#626262] text-[11.5px] font-body font-medium uppercase tracking-wider mb-4">
          Jobify Preview
        </span>

        <h1 className="font-display text-section-h2 text-[#161616] tracking-tight">
          {title}
        </h1>

        {description && (
          <p className="mt-3 font-body text-[15px] sm:text-[16px] text-[#626262] leading-relaxed">
            {description}
          </p>
        )}

        <div className="mt-6 p-4 rounded-xl bg-[#FAFAFA] border border-[#E8E8E8] text-[13.5px] text-[#626262] font-body w-full">
          This feature or view is currently in development for the next Jobify release.
        </div>

        <div className="mt-8">
          <Link
            to="/"
            className="inline-flex items-center gap-2 h-[44px] px-6 rounded-full bg-[#141414] text-white font-body text-[14px] font-medium transition-all hover:bg-[#2A2A2A] active:scale-95 shadow-sm"
          >
            <ArrowLeft className="w-4 h-4 stroke-[2]" />
            <span>Back to home</span>
          </Link>
        </div>
      </div>
    </main>
  );
}
