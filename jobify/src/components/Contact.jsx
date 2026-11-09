import React, { useState } from "react";
import { Mail, Clock, MapPin, Send, CheckCircle2, AlertCircle } from "lucide-react";
import Section from "./Section.jsx";
import Reveal from "./ui/Reveal.jsx";
import { SITE_CONTENT, SUPPORT_EMAIL } from "../data/siteContent.js";
import { cn } from "../lib/utils.js";

export default function Contact() {
  const { contact } = SITE_CONTENT;
  const [formData, setFormData] = useState({
    name: "",
    email: "",
    subject: "",
    message: "",
  });
  const [status, setStatus] = useState({ type: "idle", message: "" });
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = (e) => {
    e.preventDefault();
    const { name, email, subject, message } = formData;

    if (!name.trim() || !email.trim() || !message.trim()) {
      setStatus({
        type: "error",
        message: "Please fill in all required fields (Name, Email, Message).",
      });
      return;
    }

    if (!/^\S+@\S+\.\S+$/.test(email)) {
      setStatus({
        type: "error",
        message: "Please enter a valid email address.",
      });
      return;
    }

    setIsSubmitting(true);
    setStatus({ type: "loading", message: "Preparing your message..." });

    // Honest handling: simulate client preparation and open user's email client directly
    setTimeout(() => {
      setIsSubmitting(false);
      setStatus({
        type: "success",
        message: `Thank you, ${name}! Your inquiry has been prepared for support@jobify.app.`,
      });
      // Optionally trigger mailto link
      const mailtoUrl = `mailto:${SUPPORT_EMAIL}?subject=${encodeURIComponent(
        subject || "Jobify Inquiry"
      )}&body=${encodeURIComponent(
        `Name: ${name}\nEmail: ${email}\n\nMessage:\n${message}`
      )}`;
      window.location.href = mailtoUrl;
    }, 400);
  };

  return (
    <Section id="contact" className="py-16 md:py-24 bg-[#FAFAFA] border-t border-[#F0F0F0]">
      <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.2fr)] gap-10 lg:gap-16 items-start">
        {/* Left Column: Context & Contact Details */}
        <div className="flex flex-col text-left">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-white border border-[#E8E8E8] text-[11.5px] font-body font-medium text-[#626262] tracking-wider uppercase mb-4 w-fit">
            <span>{contact.eyebrow}</span>
          </div>

          <Reveal>
            <h2 className="font-display text-section-h2 text-[#161616] tracking-tight">
              {contact.heading}
            </h2>
            <p className="mt-3.5 font-body text-[15px] sm:text-[16px] text-[#626262] leading-relaxed max-w-[420px]">
              {contact.description}
            </p>

            {/* Contact Information List */}
            <div className="mt-8 space-y-4 text-[14px] font-body">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-white border border-[#E8E8E8] flex items-center justify-center text-[#161616]">
                  <Mail className="w-4 h-4" />
                </div>
                <div>
                  <div className="text-[12px] text-[#888888]">Support Email</div>
                  <a href={`mailto:${SUPPORT_EMAIL}`} className="font-medium text-[#161616] hover:underline">
                    {SUPPORT_EMAIL}
                  </a>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-white border border-[#E8E8E8] flex items-center justify-center text-[#161616]">
                  <Clock className="w-4 h-4" />
                </div>
                <div>
                  <div className="text-[12px] text-[#888888]">Response Window</div>
                  <div className="font-medium text-[#161616]">Within 24 business hours</div>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-white border border-[#E8E8E8] flex items-center justify-center text-[#161616]">
                  <MapPin className="w-4 h-4" />
                </div>
                <div>
                  <div className="text-[12px] text-[#888888]">Headquarters</div>
                  <div className="font-medium text-[#161616]">San Francisco, CA & Global Remote</div>
                </div>
              </div>
            </div>
          </Reveal>
        </div>

        {/* Right Column: Contact Form */}
        <div className="rounded-2xl bg-white border border-[#E8E8E8] p-6 sm:p-8 shadow-subtle text-left">
          <form onSubmit={handleSubmit} noValidate className="space-y-4 font-body">
            <div>
              <label htmlFor="contact-name" className="block text-[13px] font-medium text-[#161616] mb-1.5">
                Full Name <span className="text-[#D94B4B]">*</span>
              </label>
              <input
                id="contact-name"
                type="text"
                required
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="Alex Morgan"
                className="w-full h-11 px-3.5 rounded-lg border border-[#E8E8E8] bg-[#FDFDFD] text-[14px] text-[#161616] placeholder:text-[#AAAAAA] focus:border-[#141414] focus:bg-white outline-none transition-all"
              />
            </div>

            <div>
              <label htmlFor="contact-email" className="block text-[13px] font-medium text-[#161616] mb-1.5">
                Email Address <span className="text-[#D94B4B]">*</span>
              </label>
              <input
                id="contact-email"
                type="email"
                required
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                placeholder="alex@example.com"
                className="w-full h-11 px-3.5 rounded-lg border border-[#E8E8E8] bg-[#FDFDFD] text-[14px] text-[#161616] placeholder:text-[#AAAAAA] focus:border-[#141414] focus:bg-white outline-none transition-all"
              />
            </div>

            <div>
              <label htmlFor="contact-subject" className="block text-[13px] font-medium text-[#161616] mb-1.5">
                Subject
              </label>
              <input
                id="contact-subject"
                type="text"
                value={formData.subject}
                onChange={(e) => setFormData({ ...formData, subject: e.target.value })}
                placeholder="Job search tracking question"
                className="w-full h-11 px-3.5 rounded-lg border border-[#E8E8E8] bg-[#FDFDFD] text-[14px] text-[#161616] placeholder:text-[#AAAAAA] focus:border-[#141414] focus:bg-white outline-none transition-all"
              />
            </div>

            <div>
              <label htmlFor="contact-message" className="block text-[13px] font-medium text-[#161616] mb-1.5">
                Message <span className="text-[#D94B4B]">*</span>
              </label>
              <textarea
                id="contact-message"
                required
                rows={4}
                value={formData.message}
                onChange={(e) => setFormData({ ...formData, message: e.target.value })}
                placeholder="How can Jobify assist your current job hunt?"
                className="w-full p-3.5 rounded-lg border border-[#E8E8E8] bg-[#FDFDFD] text-[14px] text-[#161616] placeholder:text-[#AAAAAA] focus:border-[#141414] focus:bg-white outline-none transition-all resize-y"
              />
            </div>

            {/* Status Feedback Message */}
            {status.message && (
              <div
                role="status"
                aria-live="polite"
                className={cn(
                  "p-3 rounded-lg text-[13px] font-medium flex items-center gap-2",
                  status.type === "success" && "bg-[#DCFCE7] text-[#15803D]",
                  status.type === "error" && "bg-[#FEE2E2] text-[#991B1B]",
                  status.type === "loading" && "bg-[#F2F2F2] text-[#626262]"
                )}
              >
                {status.type === "success" && <CheckCircle2 className="w-4 h-4 shrink-0" />}
                {status.type === "error" && <AlertCircle className="w-4 h-4 shrink-0" />}
                <span>{status.message}</span>
              </div>
            )}

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full h-[46px] rounded-full bg-[#141414] text-white text-[14.5px] font-medium transition-all duration-150 hover:bg-[#2A2A2A] active:scale-[0.98] flex items-center justify-center gap-2 cursor-pointer shadow-sm disabled:opacity-60"
            >
              <span>{isSubmitting ? "Sending..." : "Send Message"}</span>
              <Send className="w-4 h-4" />
            </button>
          </form>
        </div>
      </div>
    </Section>
  );
}
