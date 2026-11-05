import React, { useState, useEffect, useRef } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { Menu, X } from "lucide-react";
import { Show, UserButton } from "@clerk/react";
import Logo from "./Logo.jsx";
import { NAV_LINKS } from "../data/routes.js";
import { SITE_CONTENT } from "../data/siteContent.js";
import { cn } from "../lib/utils.js";

export default function Navbar() {
  const [isScrolled, setIsScrolled] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();
  const menuButtonRef = useRef(null);

  const isHome = location.pathname === "/";

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 12);
    };
    window.addEventListener("scroll", handleScroll, { passive: true });
    handleScroll();
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  useEffect(() => {
    if (mobileMenuOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [mobileMenuOpen]);

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === "Escape" && mobileMenuOpen) {
        setMobileMenuOpen(false);
        menuButtonRef.current?.focus();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [mobileMenuOpen]);

  useEffect(() => {
    setMobileMenuOpen(false);
  }, [location.pathname, location.hash]);

  const handleLinkClick = (e, link) => {
    if (link.isAnchor) {
      if (isHome) {
        e.preventDefault();
        const el = document.getElementById(link.targetId);
        if (el) {
          el.scrollIntoView({ behavior: "smooth" });
        }
      } else {
        navigate(link.href);
      }
    }
    setMobileMenuOpen(false);
  };

  return (
    <>
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:top-4 focus:left-4 focus:z-[100] focus:px-4 focus:py-2 focus:bg-[#141414] focus:text-white focus:rounded-md focus:shadow-lg focus:outline-none"
      >
        Skip to content
      </a>

      <header
        className={cn(
          "sticky top-0 z-50 w-full transition-all duration-200",
          isScrolled
            ? "bg-white/85 backdrop-blur-md border-b border-[#E8E8E8]"
            : "bg-white border-b border-transparent"
        )}
      >
        <div className="mx-auto w-full max-w-[1120px] px-6 md:px-8 h-[68px] md:h-[72px] flex items-center justify-between">
          {/* Left: Logo */}
          <div className="flex items-center">
            <Logo variant="nav" />
          </div>

          {/* Center: Clean Nav Links */}
          <nav
            aria-label="Primary"
            className="hidden md:flex items-center gap-7 text-[14px]"
          >
            {NAV_LINKS.map((link) => (
              <a
                key={link.label}
                href={link.href}
                onClick={(e) => handleLinkClick(e, link)}
                className="font-body text-[#626262] transition-colors duration-150 hover:text-[#161616] py-1"
              >
                {link.label}
              </a>
            ))}
          </nav>

          {/* Right: Actions */}
          <div className="hidden md:flex items-center gap-4">
            <Show when="signed-out">
              <Link
                to="/signin"
                className="text-[14px] font-body text-[#626262] hover:text-[#161616] px-2 py-1 transition-colors"
              >
                {SITE_CONTENT.brand.navSignIn}
              </Link>
              <Link
                to="/signup"
                className="inline-flex items-center justify-center h-[38px] px-5 rounded-full bg-[#141414] text-white text-[13.5px] font-medium transition-all duration-150 hover:bg-[#2A2A2A] active:scale-[0.98] shadow-xs"
              >
                {SITE_CONTENT.brand.navCta}
              </Link>
            </Show>
            <Show when="signed-in">
              <Link to="/app/chat" className="text-[14px] font-body text-[#626262] hover:text-[#161616] px-2 py-1">Open app</Link>
              <UserButton />
            </Show>
          </div>

          {/* Mobile Hamburger Button */}
          <div className="flex md:hidden items-center">
            <button
              ref={menuButtonRef}
              type="button"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              aria-expanded={mobileMenuOpen}
              aria-controls="mobile-menu"
              aria-label={mobileMenuOpen ? "Close menu" : "Open menu"}
              className="w-[40px] h-[40px] flex items-center justify-center rounded-lg text-[#161616] hover:bg-[#F2F2F2] transition-colors"
            >
              {mobileMenuOpen ? (
                <X className="w-5 h-5" />
              ) : (
                <Menu className="w-5 h-5" />
              )}
            </button>
          </div>
        </div>

        {/* Mobile Navigation Drawer */}
        {mobileMenuOpen && (
          <div
            id="mobile-menu"
            className="md:hidden fixed inset-x-0 top-[68px] bottom-0 bg-white z-40 border-t border-[#E8E8E8] flex flex-col justify-between p-6 overflow-y-auto"
          >
            <nav className="flex flex-col divide-y divide-[#F2F2F2]">
              {NAV_LINKS.map((link) => (
                <a
                  key={link.label}
                  href={link.href}
                  onClick={(e) => handleLinkClick(e, link)}
                  className="flex items-center h-[52px] text-[16px] font-body text-[#161616]"
                >
                  {link.label}
                </a>
              ))}
            </nav>

            <div className="pt-6 pb-6 border-t border-[#E8E8E8] flex flex-col gap-3">
              <Show when="signed-out">
                <Link
                  to="/signin"
                  onClick={() => setMobileMenuOpen(false)}
                  className="w-full h-[44px] flex items-center justify-center rounded-full border border-[#E8E8E8] text-[#161616] text-[15px] font-medium"
                >
                  {SITE_CONTENT.brand.navSignIn}
                </Link>
                <Link
                  to="/signup"
                  onClick={() => setMobileMenuOpen(false)}
                  className="w-full h-[44px] flex items-center justify-center rounded-full bg-[#141414] text-white text-[15px] font-medium shadow-sm"
                >
                  {SITE_CONTENT.brand.navCta}
                </Link>
              </Show>
              <Show when="signed-in">
                <div className="flex items-center justify-center gap-4">
                  <Link to="/app/chat" onClick={() => setMobileMenuOpen(false)} className="text-[15px] font-medium">Open app</Link>
                  <UserButton />
                </div>
              </Show>
            </div>
          </div>
        )}
      </header>
    </>
  );
}
