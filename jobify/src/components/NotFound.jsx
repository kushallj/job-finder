import React, { useEffect } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft } from "lucide-react";

export default function NotFound() {
  useEffect(() => {
    document.title = "404 Page Not Found | Jobify";
    window.scrollTo(0, 0);
  }, []);

  return (
    <main
      id="main-content"
      className="min-h-[65vh] flex items-center justify-center py-20 px-6 sm:px-8 bg-white"
    >
      <div className="max-w-[500px] w-full text-center flex flex-col items-center">
        <span className="font-display text-[72px] font-bold text-[#161616]/15 select-none leading-none">
          404
        </span>

        <h1 className="font-display text-section-h2 text-[#161616] tracking-tight mt-2">
          Page Not Found
        </h1>

        <p className="mt-3 font-body text-[15px] sm:text-[16px] text-[#626262] leading-relaxed">
          The requested page could not be located. It may have been moved, renamed,
          or is temporarily unavailable.
        </p>

        <div className="mt-8">
          <Link
            to="/"
            className="inline-flex items-center gap-2 h-[44px] px-6 rounded-full bg-[#141414] text-white font-body text-[14px] font-medium transition-all hover:bg-[#2A2A2A] active:scale-95 shadow-sm"
          >
            <ArrowLeft className="w-4 h-4 stroke-[2]" />
            <span>Return to home</span>
          </Link>
        </div>
      </div>
    </main>
  );
}
