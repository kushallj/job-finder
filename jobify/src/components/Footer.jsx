import React from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import Logo from "./Logo.jsx";
import { SITE_CONTENT } from "../data/siteContent.js";

export default function Footer() {
  const { footer } = SITE_CONTENT;
  const location = useLocation();
  const navigate = useNavigate();

  const handleLinkClick = (e, href) => {
    if (href.startsWith("#")) {
      e.preventDefault();
      const targetId = href.replace("#", "");
      if (location.pathname === "/") {
        const el = document.getElementById(targetId);
        if (el) {
          el.scrollIntoView({ behavior: "smooth" });
        }
      } else {
        navigate(`/${href}`);
      }
    }
  };

  return (
    <footer className="w-full bg-white border-t border-[#E8E8E8] pt-16 md:pt-20 pb-12">
      <div className="mx-auto w-full max-w-[1120px] px-6 md:px-8">
        <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,1.2fr)_minmax(0,2fr)] gap-12 lg:gap-16 items-start">
          {/* Left Column: Brand & Mission */}
          <div className="flex flex-col items-start text-left max-w-[320px]">
            <Logo variant="footer" />
            <p className="mt-4 font-body text-[14px] text-[#626262] leading-relaxed">
              {footer.description}
            </p>
          </div>

          {/* Right Column: 4 Link Columns */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-8 text-left font-body">
            {footer.linkGroups.map((group) => (
              <div key={group.title} className="flex flex-col gap-3">
                <span className="text-[11.5px] font-bold text-[#888888] tracking-wider uppercase">
                  {group.title}
                </span>
                <ul className="space-y-2.5">
                  {group.links.map((link) => (
                    <li key={link.label}>
                      {link.href.startsWith("#") ? (
                        <a
                          href={link.href}
                          onClick={(e) => handleLinkClick(e, link.href)}
                          className="text-[13.5px] text-[#626262] hover:text-[#161616] transition-colors"
                        >
                          {link.label}
                        </a>
                      ) : (
                        <Link
                          to={link.href}
                          className="text-[13.5px] text-[#626262] hover:text-[#161616] transition-colors"
                        >
                          {link.label}
                        </Link>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>

        {/* Bottom Row */}
        <div className="mt-16 pt-8 border-t border-[#F0F0F0] flex flex-col sm:flex-row items-center justify-between gap-4 text-center sm:text-left text-[13px] font-body text-[#888888]">
          <p>{footer.copyright}</p>
          <div className="flex items-center gap-6">
            <Link to="/terms" className="hover:text-[#161616] transition-colors">
              Privacy Policy
            </Link>
            <Link to="/terms" className="hover:text-[#161616] transition-colors">
              Terms of Service
            </Link>
          </div>
        </div>
      </div>
    </footer>
  );
}
