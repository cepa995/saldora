"use client";

import { useState, useEffect, useRef, useSyncExternalStore } from "react";
import Image from "next/image";
import Link from "next/link";
import LandingNav from "@/components/LandingNav";

// Icons as inline SVGs
const DocumentIcon = ({ className = "w-6 h-6" }: { className?: string }) => (
  <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
  </svg>
);

const ClockIcon = ({ className = "w-6 h-6" }: { className?: string }) => (
  <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>
);

const CheckCircleIcon = ({ className = "w-6 h-6" }: { className?: string }) => (
  <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>
);

const SparklesIcon = ({ className = "w-6 h-6" }: { className?: string }) => (
  <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" />
  </svg>
);

const ShieldCheckIcon = ({ className = "w-6 h-6" }: { className?: string }) => (
  <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
  </svg>
);

const BoltIcon = ({ className = "w-6 h-6" }: { className?: string }) => (
  <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13 10V3L4 14h7v7l9-11h-7z" />
  </svg>
);

const TableCellsIcon = ({ className = "w-6 h-6" }: { className?: string }) => (
  <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3.375 19.5h17.25m-17.25 0a1.125 1.125 0 01-1.125-1.125M3.375 19.5h7.5c.621 0 1.125-.504 1.125-1.125m-9.75 0V5.625m0 12.75v-1.5c0-.621.504-1.125 1.125-1.125m18.375 2.625V5.625m0 12.75c0 .621-.504 1.125-1.125 1.125m1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125m0 3.75h-7.5A1.125 1.125 0 0112 18.375m9.75-12.75c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125m19.5 0v1.5c0 .621-.504 1.125-1.125 1.125M2.25 5.625v1.5c0 .621.504 1.125 1.125 1.125m0 0h17.25m-17.25 0h7.5c.621 0 1.125.504 1.125 1.125M3.375 8.25c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125m17.25-3.75h-7.5c-.621 0-1.125.504-1.125 1.125m8.625-1.125c.621 0 1.125.504 1.125 1.125v1.5c0 .621-.504 1.125-1.125 1.125m-17.25 0h7.5m-7.5 0c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125M12 10.875v-1.5m0 1.5c0 .621-.504 1.125-1.125 1.125M12 10.875c0 .621.504 1.125 1.125 1.125m-2.25 0c.621 0 1.125.504 1.125 1.125M13.125 12h7.5m-7.5 0c-.621 0-1.125.504-1.125 1.125M20.625 12c.621 0 1.125.504 1.125 1.125v1.5c0 .621-.504 1.125-1.125 1.125m-17.25 0h7.5M12 14.625v-1.5m0 1.5c0 .621-.504 1.125-1.125 1.125M12 14.625c0 .621.504 1.125 1.125 1.125m-2.25 0c.621 0 1.125.504 1.125 1.125m0 1.5v-1.5m0 0c0-.621.504-1.125 1.125-1.125m0 0h7.5" />
  </svg>
);

const ArrowRightIcon = ({ className = "w-5 h-5" }: { className?: string }) => (
  <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8l4 4m0 0l-4 4m4-4H3" />
  </svg>
);

const CheckIcon = ({ className = "w-5 h-5" }: { className?: string }) => (
  <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
  </svg>
);

const PlayIcon = ({ className = "w-5 h-5" }: { className?: string }) => (
  <svg className={className} fill="currentColor" viewBox="0 0 24 24">
    <path d="M8 5v14l11-7z" />
  </svg>
);

// Hook for intersection observer animations
function useInView(threshold = 0.1) {
  const ref = useRef<HTMLDivElement>(null);
  const [isInView, setIsInView] = useState(false);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) setIsInView(true);
      },
      { threshold }
    );

    if (ref.current) observer.observe(ref.current);
    return () => observer.disconnect();
  }, [threshold]);

  return { ref, isInView };
}

// Animated counter
function AnimatedCounter({ end, suffix = "" }: { end: number; suffix?: string }) {
  const [count, setCount] = useState(0);
  const { ref, isInView } = useInView();

  useEffect(() => {
    if (!isInView) return;
    let start = 0;
    const duration = 2000;
    const increment = end / (duration / 16);
    const timer = setInterval(() => {
      start += increment;
      if (start >= end) {
        setCount(end);
        clearInterval(timer);
      } else {
        setCount(Math.floor(start));
      }
    }, 16);
    return () => clearInterval(timer);
  }, [isInView, end]);

  return <span ref={ref}>{count}{suffix}</span>;
}

// Animated Background
function AnimatedBackground() {
  return (
    <div className="fixed inset-0 overflow-hidden pointer-events-none">
      <div className="absolute top-1/4 left-1/4 w-[600px] h-[600px] bg-violet-300/30 rounded-full filter blur-[120px] animate-pulse-slow" />
      <div className="absolute bottom-1/4 right-1/4 w-[500px] h-[500px] bg-indigo-300/30 rounded-full filter blur-[120px] animate-pulse-slow animation-delay-2000" />
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[700px] h-[700px] bg-pink-200/20 rounded-full filter blur-[150px] animate-pulse-slow animation-delay-4000" />
    </div>
  );
}

// Floating decorative elements
function FloatingElements() {
  return (
    <>
      {/* Floating document icon - top left */}
      <div className="absolute top-32 left-[8%] animate-float opacity-20 hidden lg:block">
        <div className="w-14 h-18 rounded-lg border-2 border-violet-400 flex items-center justify-center p-2">
          <div className="space-y-1">
            <div className="w-7 h-1 bg-violet-400 rounded" />
            <div className="w-5 h-1 bg-violet-400 rounded" />
            <div className="w-6 h-1 bg-violet-400 rounded" />
          </div>
        </div>
      </div>

      {/* Another document - lower left, slightly rotated */}
      <div className="absolute top-[55%] left-[3%] animate-float-delayed opacity-15 hidden lg:block" style={{ animationDelay: "1s" }}>
        <div className="w-12 h-16 rounded-lg border-2 border-indigo-300 flex items-center justify-center rotate-[-8deg]">
          <div className="space-y-1">
            <div className="w-6 h-1 bg-indigo-300 rounded" />
            <div className="w-4 h-1 bg-indigo-300 rounded" />
            <div className="w-5 h-1 bg-indigo-300 rounded" />
          </div>
        </div>
      </div>

      {/* Floating check - top right area */}
      <div className="absolute top-40 right-[12%] animate-float-delayed opacity-20 hidden lg:block">
        <div className="w-10 h-10 rounded-full border-2 border-emerald-400 flex items-center justify-center">
          <CheckIcon className="w-5 h-5 text-emerald-400" />
        </div>
      </div>

      {/* Currency symbol - left side */}
      <div className="absolute top-[40%] left-[12%] animate-bounce-slow opacity-15 hidden lg:block">
        <div className="w-10 h-10 rounded-full border-2 border-cyan-400 flex items-center justify-center">
          <span className="text-cyan-400 font-bold text-sm">€</span>
        </div>
      </div>

      {/* Floating dots grid - bottom left */}
      <div className="absolute bottom-32 left-[6%] animate-bounce-slow opacity-10 hidden lg:block">
        <div className="grid grid-cols-3 gap-1.5">
          {[...Array(9)].map((_, i) => (
            <div key={i} className="w-1.5 h-1.5 bg-violet-500 rounded-full" />
          ))}
        </div>
      </div>

      {/* Floating sparkle - right */}
      <div className="absolute top-[30%] right-[10%] animate-spin-slow opacity-20 hidden lg:block">
        <SparklesIcon className="w-8 h-8 text-amber-400" />
      </div>

      {/* Small table/grid icon - representing Excel */}
      <div className="absolute bottom-[35%] left-[5%] animate-float opacity-15 hidden lg:block" style={{ animationDelay: "0.5s" }}>
        <div className="w-10 h-10 rounded-lg border-2 border-emerald-400 p-1.5">
          <div className="grid grid-cols-3 gap-0.5 h-full">
            {[...Array(9)].map((_, i) => (
              <div key={i} className="bg-emerald-400 rounded-sm" />
            ))}
          </div>
        </div>
      </div>

      {/* Percentage badge - right side */}
      <div className="absolute top-[60%] right-[5%] animate-float-delayed opacity-15 hidden lg:block">
        <div className="w-12 h-12 rounded-xl border-2 border-violet-400 flex items-center justify-center">
          <span className="text-violet-400 font-bold text-xs">98%</span>
        </div>
      </div>

      {/* Small bolt icon */}
      <div className="absolute bottom-48 right-[15%] animate-bounce-slow opacity-20 hidden lg:block">
        <BoltIcon className="w-6 h-6 text-amber-400" />
      </div>
    </>
  );
}

// Hero Section
function HeroSection() {
  const mounted = useSyncExternalStore(
    () => () => {},
    () => true,
    () => false,
  );

  return (
    <section className="relative min-h-screen flex items-center overflow-hidden bg-gradient-to-b from-violet-50/50 via-white to-white">
      {/* Grid pattern overlay */}
      <div className="absolute inset-0 bg-[linear-gradient(rgba(139,92,246,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(139,92,246,0.03)_1px,transparent_1px)] bg-[size:60px_60px]" />

      {/* Radial gradient accent */}
      <div className="absolute top-0 right-0 w-[600px] h-[600px] bg-gradient-to-br from-violet-200/40 to-transparent rounded-full blur-3xl" />
      <div className="absolute bottom-0 left-0 w-[400px] h-[400px] bg-gradient-to-tr from-indigo-200/30 to-transparent rounded-full blur-3xl" />

      <FloatingElements />

      <div className="relative max-w-7xl mx-auto px-6 pt-32 pb-20">
        <div className="grid lg:grid-cols-2 gap-12 lg:gap-16 items-center">
          <div>
            {/* Badge with new indicator */}
            <div className={`inline-flex items-center gap-3 px-4 py-2 bg-white rounded-full shadow-lg shadow-violet-500/10 border border-violet-100 mb-8 transition-all duration-700 ${mounted ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4"}`}>
              <span className="px-2 py-0.5 bg-violet-600 text-white text-[10px] font-bold uppercase rounded-full tracking-wider">Novo</span>
              <span className="text-sm text-gray-600">AI-powered OCR za Srbiju</span>
              <div className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-pulse" />
            </div>

            <h1 className={`text-5xl lg:text-7xl font-bold tracking-tight text-gray-900 mb-6 transition-all duration-700 delay-100 ${mounted ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4"}`}>
              Fakture.
              <br />
              <span className="relative">
                <span className="bg-gradient-to-r from-violet-600 via-indigo-600 to-violet-600 bg-clip-text text-transparent bg-[size:200%_auto] animate-gradient">Automatski.</span>
                {/* Underline decoration */}
                <svg className="absolute -bottom-2 left-0 w-full h-3 text-violet-300" viewBox="0 0 200 8" preserveAspectRatio="none">
                  <path d="M0 7 Q50 0, 100 7 T200 7" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
                </svg>
              </span>
            </h1>

            <p className={`text-xl text-gray-600 leading-relaxed mb-10 max-w-lg transition-all duration-700 delay-200 ${mounted ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4"}`}>
              AI izvlači podatke iz svih vaših faktura za sekunde.
              <span className="text-violet-600 font-medium"> Ćirilica, latinica</span>, bilo koji format.
            </p>

            <div className={`flex flex-wrap gap-4 mb-10 transition-all duration-700 delay-300 ${mounted ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4"}`}>
              <a href="#kontakt" className="group inline-flex items-center gap-2 px-8 py-4 bg-gradient-to-r from-violet-600 to-indigo-600 text-white font-medium rounded-xl transition-all duration-300 hover:scale-105 hover:shadow-2xl hover:shadow-violet-500/30">
                Isprobaj besplatno
                <ArrowRightIcon className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
              </a>
              <a href="#kako-radi" className="group inline-flex items-center gap-2 px-8 py-4 bg-white text-gray-700 font-medium rounded-xl border border-gray-200 hover:border-violet-300 hover:shadow-lg hover:shadow-violet-500/10 transition-all duration-300">
                <div className="w-8 h-8 bg-violet-100 rounded-lg flex items-center justify-center group-hover:bg-violet-200 transition-colors">
                  <PlayIcon className="w-4 h-4 text-violet-600" />
                </div>
                Pogledaj demo
              </a>
            </div>

            {/* Stats with icons */}
            <div className={`flex items-center gap-8 lg:gap-10 mb-10 transition-all duration-700 delay-400 ${mounted ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4"}`}>
              {[
                { value: 98, suffix: "%", label: "Tačnost", icon: "🎯", color: "violet" },
                { value: 10, suffix: "x", label: "Brže", icon: "⚡", color: "amber" },
                { value: 500, suffix: "+", label: "Faktura/dan", icon: "📄", color: "emerald" },
              ].map((stat, i) => (
                <div key={i} className="group text-center">
                  <div className="flex items-center gap-2 justify-center mb-1">
                    <span className="text-lg">{stat.icon}</span>
                    <div className="text-3xl font-bold text-gray-900 group-hover:text-violet-600 transition-colors">
                      <AnimatedCounter end={stat.value} suffix={stat.suffix} />
                    </div>
                  </div>
                  <div className="text-sm text-gray-500">{stat.label}</div>
                </div>
              ))}
            </div>

            {/* Trust badges */}
            <div className={`transition-all duration-700 delay-500 ${mounted ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4"}`}>
              <div className="flex flex-wrap items-center gap-4">
                <div className="flex items-center gap-2 px-3 py-2 bg-gray-50 rounded-lg border border-gray-100">
                  <ShieldCheckIcon className="w-4 h-4 text-emerald-500" />
                  <span className="text-xs text-gray-600 font-medium">GDPR usklađeno</span>
                </div>
                <div className="flex items-center gap-2 px-3 py-2 bg-gray-50 rounded-lg border border-gray-100">
                  <svg className="w-4 h-4 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                  </svg>
                  <span className="text-xs text-gray-600 font-medium">SSL enkripcija</span>
                </div>
                <div className="flex items-center gap-2 px-3 py-2 bg-gray-50 rounded-lg border border-gray-100">
                  <svg className="w-4 h-4 text-violet-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                  </svg>
                  <span className="text-xs text-gray-600 font-medium">APR verifikacija</span>
                </div>
              </div>
            </div>
          </div>

          {/* Interactive Demo Card */}
          <div className={`relative transition-all duration-1000 delay-300 ${mounted ? "opacity-100 translate-y-0" : "opacity-0 translate-y-10"}`}>
            {/* Background glow */}
            <div className="absolute -inset-4 bg-gradient-to-r from-violet-200 via-indigo-200 to-violet-200 rounded-[2rem] blur-2xl opacity-50" />

            <div className="relative bg-white rounded-3xl shadow-2xl shadow-violet-200/50 p-6 lg:p-8 border border-gray-100/50 group hover:shadow-violet-300/50 transition-shadow duration-500">
              {/* Corner brackets */}
              <div className="absolute -top-2 -left-2 w-5 h-5 border-t-2 border-l-2 border-violet-400 rounded-tl-lg" />
              <div className="absolute -top-2 -right-2 w-5 h-5 border-t-2 border-r-2 border-violet-400 rounded-tr-lg" />
              <div className="absolute -bottom-2 -left-2 w-5 h-5 border-b-2 border-l-2 border-violet-400 rounded-bl-lg" />
              <div className="absolute -bottom-2 -right-2 w-5 h-5 border-b-2 border-r-2 border-violet-400 rounded-br-lg" />

              {/* Header */}
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-red-400" />
                  <div className="w-3 h-3 rounded-full bg-amber-400" />
                  <div className="w-3 h-3 rounded-full bg-emerald-400" />
                </div>
                <div className="flex items-center gap-2 px-3 py-1 bg-violet-50 rounded-full">
                  <div className="w-2 h-2 bg-violet-500 rounded-full animate-pulse" />
                  <span className="text-xs font-medium text-violet-600">AI obrađuje</span>
                </div>
              </div>

              {/* Invoice mockup - more realistic */}
              <div className="relative bg-gradient-to-br from-gray-50 to-white rounded-2xl p-5 mb-5 overflow-hidden border border-gray-100">
                {/* Invoice header */}
                <div className="flex justify-between items-start mb-4">
                  <div>
                    <div className="text-[10px] font-bold text-gray-800 uppercase tracking-wider mb-1">ФАКТУРА</div>
                    <div className="text-[8px] text-gray-400">Br: 2025-00042</div>
                  </div>
                  <div className="text-right">
                    <div className="text-[8px] text-gray-400 mb-1">Datum izdavanja</div>
                    <div className="text-[9px] font-medium text-gray-600">15.01.2025.</div>
                  </div>
                </div>

                {/* Invoice body skeleton */}
                <div className="space-y-3">
                  <div className="flex gap-3">
                    <div className="flex-1 p-2 bg-gray-100/50 rounded-lg">
                      <div className="text-[7px] text-gray-400 uppercase mb-1">Prodavac</div>
                      <div className="h-1.5 w-full bg-gray-200 rounded mb-1" />
                      <div className="h-1 w-3/4 bg-gray-200 rounded" />
                      <div className="mt-1.5 px-1.5 py-0.5 bg-violet-100 rounded inline-block">
                        <span className="text-[6px] font-mono text-violet-600">PIB: 123456789</span>
                      </div>
                    </div>
                    <div className="flex-1 p-2 bg-gray-100/50 rounded-lg">
                      <div className="text-[7px] text-gray-400 uppercase mb-1">Kupac</div>
                      <div className="h-1.5 w-full bg-gray-200 rounded mb-1" />
                      <div className="h-1 w-2/3 bg-gray-200 rounded" />
                    </div>
                  </div>

                  {/* Items */}
                  <div className="border border-gray-100 rounded-lg overflow-hidden">
                    <div className="grid grid-cols-4 gap-1 px-2 py-1.5 bg-gray-100/70">
                      <div className="text-[6px] font-semibold text-gray-500 col-span-2">OPIS</div>
                      <div className="text-[6px] font-semibold text-gray-500 text-right">KOL.</div>
                      <div className="text-[6px] font-semibold text-gray-500 text-right">CENA</div>
                    </div>
                    {[1, 2].map((_, i) => (
                      <div key={i} className="grid grid-cols-4 gap-1 px-2 py-1.5 border-t border-gray-100">
                        <div className="col-span-2"><div className="h-1.5 w-full bg-gray-200 rounded" /></div>
                        <div className="text-right"><div className="h-1.5 w-3 bg-gray-200 rounded ml-auto" /></div>
                        <div className="text-right"><div className="h-1.5 w-5 bg-gray-200 rounded ml-auto" /></div>
                      </div>
                    ))}
                  </div>

                  {/* Totals */}
                  <div className="flex justify-end">
                    <div className="w-28 space-y-1">
                      <div className="flex justify-between text-[7px]">
                        <span className="text-gray-400">Osnovica:</span>
                        <div className="h-2 w-10 bg-gray-200 rounded" />
                      </div>
                      <div className="flex justify-between text-[7px]">
                        <span className="text-gray-400">PDV 20%:</span>
                        <div className="h-2 w-7 bg-cyan-200 rounded" />
                      </div>
                      <div className="flex justify-between text-[7px] pt-1 border-t border-gray-200">
                        <span className="font-semibold text-gray-600">UKUPNO:</span>
                        <div className="h-2.5 w-12 bg-emerald-300 rounded" />
                      </div>
                    </div>
                  </div>
                </div>

                {/* Scanning overlay */}
                <div className="absolute inset-0 bg-gradient-to-b from-violet-500/5 to-transparent pointer-events-none" />
                {/* Scan line */}
                <div className="absolute inset-x-0 h-0.5 bg-gradient-to-r from-transparent via-violet-500 to-transparent animate-scan" style={{ boxShadow: '0 0 8px 2px rgba(139, 92, 246, 0.4)' }} />

                {/* Highlight boxes */}
                <div className="absolute top-[52px] left-[14px] w-[52px] h-[12px] border border-violet-400 rounded bg-violet-400/10 animate-pulse" />
                <div className="absolute bottom-[22px] right-[14px] w-[48px] h-[10px] border border-emerald-400 rounded bg-emerald-400/10 animate-pulse" style={{ animationDelay: '500ms' }} />
              </div>

              {/* Extracted data with icons */}
              <div className="space-y-2">
                {[
                  { label: "PIB", value: "123456789", icon: "🏢", gradient: "from-violet-500 to-indigo-500", bg: "bg-violet-50", verified: true },
                  { label: "Iznos", value: "45.000,00 RSD", icon: "💰", gradient: "from-emerald-500 to-teal-500", bg: "bg-emerald-50", verified: true },
                  { label: "PDV (20%)", value: "9.000,00 RSD", icon: "📊", gradient: "from-cyan-500 to-blue-500", bg: "bg-cyan-50", verified: true },
                ].map((item, i) => (
                  <div
                    key={i}
                    className={`relative flex items-center justify-between p-3 ${item.bg} rounded-xl border border-gray-100 overflow-hidden hover:shadow-md transition-all duration-300`}
                    style={{ animationDelay: `${i * 100}ms` }}
                  >
                    {/* Left gradient accent */}
                    <div className={`absolute left-0 top-0 bottom-0 w-1 bg-gradient-to-b ${item.gradient}`} />

                    <div className="flex items-center gap-2 pl-2">
                      <span className="text-sm">{item.icon}</span>
                      <span className="text-sm text-gray-600">{item.label}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-mono font-semibold text-gray-800">{item.value}</span>
                      {item.verified && (
                        <div className="w-5 h-5 bg-emerald-500 rounded-full flex items-center justify-center">
                          <CheckIcon className="w-3 h-3 text-white" />
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>

              {/* Success badge */}
              <div className="absolute -top-4 -right-4 px-4 py-2 bg-gradient-to-r from-emerald-500 to-teal-500 text-white text-sm font-medium rounded-full shadow-lg shadow-emerald-500/30 animate-bounce-slow flex items-center gap-2">
                <ClockIcon className="w-4 h-4" />
                2.3s
              </div>
            </div>

            {/* Floating cards */}
            {/* Left - Processing file */}
            <div className="absolute -left-6 lg:-left-10 top-1/3 bg-white rounded-2xl shadow-xl shadow-violet-200/50 p-4 animate-float border border-gray-100 hidden sm:block">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-gradient-to-br from-violet-100 to-indigo-100 rounded-xl flex items-center justify-center">
                  <DocumentIcon className="w-5 h-5 text-violet-600" />
                </div>
                <div>
                  <div className="text-sm font-medium text-gray-900">faktura_042.pdf</div>
                  <div className="flex items-center gap-1">
                    <div className="w-12 h-1 bg-gray-200 rounded-full overflow-hidden">
                      <div className="h-full w-3/4 bg-violet-500 rounded-full animate-pulse" />
                    </div>
                    <span className="text-[10px] text-gray-400">75%</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Top right - Export format */}
            <div className="absolute -right-2 lg:-right-6 top-8 bg-white rounded-xl shadow-lg shadow-emerald-200/50 px-3 py-2 animate-float-delayed border border-gray-100 hidden sm:block" style={{ animationDelay: "0.3s" }}>
              <div className="flex items-center gap-2">
                <div className="w-7 h-7 bg-emerald-100 rounded-lg flex items-center justify-center">
                  <TableCellsIcon className="w-4 h-4 text-emerald-600" />
                </div>
                <div>
                  <div className="text-[10px] text-gray-400">Export</div>
                  <div className="text-xs font-semibold text-emerald-600">.xlsx</div>
                </div>
              </div>
            </div>

            {/* Right middle - Verified badge */}
            <div className="absolute -right-2 lg:-right-6 bottom-1/3 bg-white rounded-2xl shadow-xl shadow-emerald-200/50 p-3 animate-float-delayed border border-gray-100 hidden sm:block">
              <div className="flex items-center gap-2 text-emerald-600">
                <div className="w-8 h-8 bg-emerald-100 rounded-lg flex items-center justify-center">
                  <CheckCircleIcon className="w-5 h-5" />
                </div>
                <div>
                  <div className="text-sm font-medium">Verifikovano</div>
                  <div className="text-[10px] text-emerald-500">APR baza</div>
                </div>
              </div>
            </div>

            {/* Bottom left - Speed indicator */}
            <div className="absolute -left-2 lg:-left-4 bottom-12 bg-white rounded-lg shadow-md shadow-amber-200/50 px-3 py-2 animate-bounce-slow border border-gray-100 hidden sm:block">
              <div className="flex items-center gap-1.5">
                <BoltIcon className="w-4 h-4 text-amber-500" />
                <span className="text-xs font-semibold text-amber-600">10x brže</span>
              </div>
            </div>

            {/* AI indicator floating */}
            <div className="absolute left-1/2 -translate-x-1/2 -bottom-6 bg-gradient-to-r from-violet-600 to-indigo-600 text-white px-4 py-2 rounded-full shadow-lg flex items-center gap-2 text-sm font-medium">
              <SparklesIcon className="w-4 h-4" />
              AI ekstrahuje podatke
            </div>
          </div>
        </div>

        {/* Trusted by section */}
        {/* <div className={`mt-20 transition-all duration-700 delay-600 ${mounted ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4"}`}>
          <p className="text-center text-sm text-gray-400 mb-6">Koriste računovodstvene agencije širom Srbije</p>
          <div className="flex items-center justify-center gap-8 lg:gap-12 opacity-40 grayscale hover:grayscale-0 hover:opacity-60 transition-all duration-500">
            {[
              { name: "Agencija 1", width: "w-24" },
              { name: "Agencija 2", width: "w-28" },
              { name: "Agencija 3", width: "w-20" },
              { name: "Agencija 4", width: "w-24" },
              { name: "Agencija 5", width: "w-28" },
            ].map((company, i) => (
              <div key={i} className={`${company.width} h-8 bg-gray-300 rounded-lg flex items-center justify-center`}>
                <span className="text-xs text-gray-500 font-medium">{company.name}</span>
              </div>
            ))}
          </div>
        </div> */}
      </div>

      {/* Scroll indicator */}
      <div className="absolute bottom-8 left-1/2 -translate-x-1/2 animate-bounce-slow">
        <div className="flex flex-col items-center gap-2">
          <span className="text-xs text-gray-400">Saznaj više</span>
          <div className="w-6 h-10 rounded-full border-2 border-gray-300 flex items-start justify-center p-2">
            <div className="w-1 h-2 bg-gray-400 rounded-full animate-scroll-indicator" />
          </div>
        </div>
      </div>
    </section>
  );
}

// AI Avatar Component - Scanning Eye Design
function AIAvatar({ className = "" }: { className?: string }) {
  return (
    <div className={`relative ${className}`}>
      {/* Outer glow */}
      <div className="absolute inset-0 bg-gradient-to-br from-violet-500 to-indigo-500 rounded-full blur-2xl opacity-40 animate-pulse-slow" />

      {/* Main container */}
      <div className="relative w-20 h-20">
        {/* Background with gradient border */}
        <div className="absolute inset-0 rounded-2xl bg-gradient-to-br from-violet-600 via-indigo-600 to-violet-700 p-[2px] rotate-45">
          <div className="w-full h-full rounded-2xl bg-gray-900" />
        </div>

        {/* Eye container - centered */}
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="relative w-14 h-14">
            {/* Eye outer ring */}
            <div className="absolute inset-0 rounded-full border-2 border-violet-500/50" />

            {/* Eye middle ring */}
            <div className="absolute inset-2 rounded-full border border-indigo-400/30" />

            {/* Iris */}
            <div className="absolute inset-3 rounded-full bg-gradient-to-br from-violet-600 to-indigo-700">
              {/* Pupil */}
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="w-4 h-4 rounded-full bg-gray-900 flex items-center justify-center">
                  {/* Inner glow */}
                  <div className="w-2 h-2 rounded-full bg-violet-400 animate-pulse" />
                </div>
              </div>

              {/* Light reflection */}
              <div className="absolute top-1.5 right-2 w-1.5 h-1.5 rounded-full bg-white/60" />
            </div>

            {/* Scanning laser line */}
            <div className="absolute inset-x-0 top-1/2 -translate-y-1/2 h-[2px] overflow-hidden">
              <div className="h-full w-full bg-gradient-to-r from-transparent via-cyan-400 to-transparent animate-scan-horizontal" />
            </div>

            {/* Scan rings emanating */}
            <div className="absolute inset-0 rounded-full border border-cyan-400/20 animate-ping" style={{ animationDuration: "2s" }} />
          </div>
        </div>

        {/* Corner accents */}
        <div className="absolute top-0 left-1/2 -translate-x-1/2 -translate-y-1 w-3 h-3 border-t-2 border-violet-400/60" />
        <div className="absolute bottom-0 left-1/2 -translate-x-1/2 translate-y-1 w-3 h-3 border-b-2 border-violet-400/60" />
      </div>
    </div>
  );
}

// Before/After Transformation Section
function TransformationSection() {
  const { ref, isInView } = useInView();
  const [showAfter, setShowAfter] = useState(false);

  useEffect(() => {
    if (isInView) {
      const timer = setTimeout(() => setShowAfter(true), 800);
      return () => clearTimeout(timer);
    }
  }, [isInView]);

  return (
    <section className="relative py-32 bg-gray-900 overflow-hidden">
      {/* Animated gradient orbs */}
      <div className="absolute top-0 left-1/4 w-96 h-96 bg-violet-600 rounded-full filter blur-[120px] opacity-20 animate-pulse-slow" />
      <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-indigo-600 rounded-full filter blur-[120px] opacity-20 animate-pulse-slow animation-delay-2000" />

      <div className="relative max-w-7xl mx-auto px-6">
        <div ref={ref} className="text-center mb-16">
          <div className={`inline-flex items-center gap-2 px-4 py-2 bg-white/10 backdrop-blur rounded-full mb-6 transition-all duration-700 ${isInView ? "opacity-100 translate-y-0" : "opacity-0 translate-y-10"}`}>
            <SparklesIcon className="w-4 h-4 text-violet-400" />
            <span className="text-sm font-medium text-violet-300">Transformacija</span>
          </div>
          <h2 className={`text-4xl lg:text-5xl font-bold text-white mb-6 transition-all duration-700 delay-100 ${isInView ? "opacity-100 translate-y-0" : "opacity-0 translate-y-10"}`}>
            Od haosa do kontrole
          </h2>
          <p className={`text-xl text-gray-400 max-w-2xl mx-auto transition-all duration-700 delay-200 ${isInView ? "opacity-100 translate-y-0" : "opacity-0 translate-y-10"}`}>
            Pogledajte kako FakturaAI transformiše vaš radni dan
          </p>
        </div>

        {/* Before/After Comparison */}
        <div className={`grid lg:grid-cols-2 gap-8 lg:gap-4 items-stretch transition-all duration-700 delay-300 ${isInView ? "opacity-100 translate-y-0" : "opacity-0 translate-y-20"}`}>

          {/* BEFORE - Old Way */}
          <div className={`relative transition-all duration-700 ${showAfter ? "opacity-60 scale-[0.98]" : "opacity-100 scale-100"}`}>
            {/* Badge - fixed z-index */}
            <div className="absolute -top-4 left-4 z-20 px-4 py-1.5 bg-red-500/20 border border-red-500/30 text-red-400 text-sm font-semibold rounded-full backdrop-blur-sm">
              Stari način
            </div>
            <div className="bg-gradient-to-br from-gray-800 to-gray-900 rounded-3xl p-8 border border-red-500/20 relative overflow-hidden h-full min-h-[480px] flex flex-col">
              {/* Chaos visualization */}
              <div className="flex-1 flex flex-col">
                {/* Scattered papers animation */}
                <div className="relative h-36 mb-6">
                  {[...Array(5)].map((_, i) => (
                    <div
                      key={i}
                      className="absolute w-14 h-18 bg-gray-700 rounded-lg border border-gray-600 shadow-lg"
                      style={{
                        left: `${10 + i * 16}%`,
                        top: `${5 + (i % 3) * 25}%`,
                        transform: `rotate(${-15 + i * 8}deg)`,
                        zIndex: i,
                      }}
                    >
                      <div className="p-2 space-y-1">
                        <div className="h-1.5 w-6 bg-gray-600 rounded" />
                        <div className="h-1 w-4 bg-gray-600 rounded" />
                        <div className="h-1 w-8 bg-gray-600 rounded" />
                      </div>
                    </div>
                  ))}
                  {/* Stressed icon */}
                  <div className="absolute right-2 bottom-0 text-4xl animate-bounce-slow">😫</div>
                </div>

                {/* Pain points */}
                <div className="space-y-3 flex-1">
                  {[
                    { icon: "⏱️", text: "3-5 minuta po fakturi", subtext: "Ručni unos podataka" },
                    { icon: "❌", text: "5-10% grešaka", subtext: "Ljudski faktor" },
                    { icon: "📚", text: "Gomila papira", subtext: "Neorganizovano" },
                  ].map((item, i) => (
                    <div key={i} className="flex items-center gap-4 p-3 bg-red-500/5 border border-red-500/10 rounded-xl">
                      <span className="text-2xl">{item.icon}</span>
                      <div>
                        <div className="text-white font-medium">{item.text}</div>
                        <div className="text-gray-500 text-sm">{item.subtext}</div>
                      </div>
                    </div>
                  ))}
                </div>

                {/* Time waste indicator */}
                <div className="mt-6 p-4 bg-red-500/10 border border-red-500/20 rounded-2xl">
                  <div className="flex items-center justify-between">
                    <span className="text-gray-400">Mesečno izgubljeno:</span>
                    <span className="text-2xl font-bold text-red-400">40+ sati</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Arrow / Transformation indicator */}
          <div className="hidden lg:flex absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-30">
            <div className={`w-20 h-20 rounded-full bg-gradient-to-r from-violet-600 to-indigo-600 flex items-center justify-center shadow-2xl shadow-violet-500/50 transition-all duration-500 ${showAfter ? "scale-110" : "scale-100"}`}>
              <ArrowRightIcon className="w-8 h-8 text-white" />
            </div>
          </div>

          {/* AFTER - New Way */}
          <div className={`relative transition-all duration-700 delay-500 ${showAfter ? "opacity-100 scale-100" : "opacity-40 scale-[0.98]"}`}>
            {/* Badge - fixed z-index */}
            <div className="absolute -top-4 right-4 z-20 px-4 py-1.5 bg-emerald-500/20 border border-emerald-500/30 text-emerald-400 text-sm font-semibold rounded-full backdrop-blur-sm">
              Sa FakturaAI
            </div>
            <div className="bg-gradient-to-br from-gray-800 to-gray-900 rounded-3xl p-8 border border-emerald-500/20 relative overflow-hidden h-full min-h-[480px] flex flex-col">
              {/* Glow effect */}
              <div className="absolute -inset-px rounded-3xl bg-gradient-to-br from-emerald-500 to-teal-500 opacity-10 blur-xl" />

              <div className="relative flex-1 flex flex-col">
                {/* Organized visualization with AI Avatar */}
                <div className="relative h-36 mb-6">
                  {/* Neat stack of processed invoices */}
                  <div className="absolute left-4 top-2">
                    {[...Array(3)].map((_, i) => (
                      <div
                        key={i}
                        className="absolute w-16 h-20 bg-gradient-to-br from-gray-700 to-gray-800 rounded-xl border border-emerald-500/30 shadow-lg shadow-emerald-500/10"
                        style={{
                          top: `${i * 4}px`,
                          left: `${i * 4}px`,
                          zIndex: 3 - i,
                        }}
                      >
                        <div className="p-2 space-y-1">
                          <div className="h-1.5 w-8 bg-emerald-500/50 rounded" />
                          <div className="h-1 w-6 bg-gray-600 rounded" />
                          <div className="h-1 w-10 bg-gray-600 rounded" />
                          <div className="mt-1.5 flex items-center gap-1">
                            <div className="w-2.5 h-2.5 rounded-full bg-emerald-500 flex items-center justify-center">
                              <CheckIcon className="w-1.5 h-1.5 text-white" />
                            </div>
                            <span className="text-[7px] text-emerald-400">OK</span>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* AI Avatar in center-right */}
                  <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2">
                    <AIAvatar />
                  </div>

                  {/* Data output - Excel */}
                  <div className="absolute right-2 top-2">
                    <div className="w-20 h-16 bg-gradient-to-br from-violet-600/20 to-indigo-600/20 rounded-xl border border-violet-500/30 p-1.5">
                      <div className="grid grid-cols-3 gap-0.5">
                        {[...Array(9)].map((_, i) => (
                          <div key={i} className={`h-1.5 rounded ${i < 3 ? "bg-violet-500/50" : "bg-gray-600/50"}`} />
                        ))}
                      </div>
                      <div className="mt-1.5 text-[7px] text-violet-400 text-center font-medium">Excel</div>
                    </div>
                  </div>

                  {/* Happy icon */}
                  <div className="absolute right-2 bottom-0 text-3xl">😊</div>
                </div>

                {/* Benefits */}
                <div className="space-y-3 flex-1">
                  {[
                    { icon: "⚡", text: "5 sekundi po fakturi", subtext: "Automatska obrada" },
                    { icon: "✅", text: "98% tačnost", subtext: "AI preciznost" },
                    { icon: "📊", text: "Strukturirani podaci", subtext: "Spremno za export" },
                  ].map((item, i) => (
                    <div key={i} className="flex items-center gap-4 p-3 bg-emerald-500/5 border border-emerald-500/10 rounded-xl">
                      <span className="text-2xl">{item.icon}</span>
                      <div>
                        <div className="text-white font-medium">{item.text}</div>
                        <div className="text-gray-500 text-sm">{item.subtext}</div>
                      </div>
                    </div>
                  ))}
                </div>

                {/* Time saved indicator */}
                <div className="mt-6 p-4 bg-emerald-500/10 border border-emerald-500/20 rounded-2xl">
                  <div className="flex items-center justify-between">
                    <span className="text-gray-400">Mesečno uštedite:</span>
                    <span className="text-2xl font-bold text-emerald-400">10+ sati</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Stats row below */}
        <div className={`grid grid-cols-2 md:grid-cols-4 gap-4 mt-16 transition-all duration-700 delay-700 ${isInView ? "opacity-100 translate-y-0" : "opacity-0 translate-y-10"}`}>
          {[
            { value: "36x", label: "Brža obrada", icon: "⚡", gradient: "from-amber-500 to-orange-500" },
            { value: "98%", label: "Tačnost", icon: "🎯", gradient: "from-emerald-500 to-teal-500" },
            { value: "0", label: "Ručnog unosa", icon: "🤖", gradient: "from-violet-500 to-indigo-500" },
            { value: "24/7", label: "Dostupnost", icon: "🌐", gradient: "from-cyan-500 to-blue-500" },
          ].map((stat, i) => (
            <div
              key={i}
              className="group relative text-center p-6 bg-gradient-to-br from-white/[0.08] to-white/[0.02] backdrop-blur rounded-2xl border border-white/10 hover:border-white/20 transition-all duration-500 hover:-translate-y-1 hover:shadow-lg hover:shadow-violet-500/10 overflow-hidden"
              style={{ animationDelay: `${i * 100}ms` }}
            >
              {/* Gradient glow on hover */}
              <div className={`absolute inset-0 bg-gradient-to-br ${stat.gradient} opacity-0 group-hover:opacity-10 transition-opacity duration-500`} />

              {/* Icon */}
              <div className="text-2xl mb-2 group-hover:scale-110 transition-transform duration-300">{stat.icon}</div>

              {/* Value with gradient */}
              <div className={`text-3xl lg:text-4xl font-bold mb-1 bg-gradient-to-r ${stat.gradient} bg-clip-text text-transparent`}>
                {stat.value}
              </div>

              {/* Label */}
              <div className="text-sm text-gray-400 group-hover:text-gray-300 transition-colors">{stat.label}</div>

              {/* Bottom accent line */}
              <div className={`absolute bottom-0 left-1/2 -translate-x-1/2 w-0 h-0.5 bg-gradient-to-r ${stat.gradient} group-hover:w-1/2 transition-all duration-500`} />
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

// How It Works - Interactive Process
function HowItWorksSection() {
  const { ref, isInView } = useInView();
  const [activeStep, setActiveStep] = useState(0);

  useEffect(() => {
    if (!isInView) return;
    const interval = setInterval(() => {
      setActiveStep((prev) => (prev + 1) % 3);
    }, 3000);
    return () => clearInterval(interval);
  }, [isInView]);

  const steps = [
    {
      num: "01",
      title: "Učitajte fakture",
      description: "Prevucite PDF, slike ili skenirane dokumente. Podržavamo batch upload stotina faktura odjednom.",
      gradient: "from-violet-500 to-indigo-500",
    },
    {
      num: "02",
      title: "AI obrađuje",
      description: "Naš AI prepoznaje strukturu dokumenta, čita ćirilicu i latinicu, i izvlači sve podatke.",
      gradient: "from-indigo-500 to-cyan-500",
    },
    {
      num: "03",
      title: "Preuzmite podatke",
      description: "Dobijate strukturirane podatke spremne za Excel, CSV ili direktan uvoz u vaš softver.",
      gradient: "from-cyan-500 to-emerald-500",
    },
  ];

  return (
    <section id="kako-radi" className="py-32 bg-gradient-to-b from-white to-violet-50/30 relative overflow-hidden">
      {/* Decorative elements */}
      <div className="absolute top-20 right-10 w-64 h-64 bg-violet-200 rounded-full filter blur-3xl opacity-30" />
      <div className="absolute bottom-20 left-10 w-64 h-64 bg-indigo-200 rounded-full filter blur-3xl opacity-30" />

      <div className="relative max-w-7xl mx-auto px-6">
        <div ref={ref} className="text-center mb-16">
          <div className={`inline-flex items-center gap-2 px-4 py-2 bg-violet-100 rounded-full mb-6 transition-all duration-700 ${isInView ? "opacity-100 translate-y-0" : "opacity-0 translate-y-10"}`}>
            <SparklesIcon className="w-4 h-4 text-violet-600" />
            <span className="text-sm font-medium text-violet-600">Kako radi</span>
          </div>
          <h2 className={`text-4xl lg:text-5xl font-bold text-gray-900 mb-6 transition-all duration-700 delay-100 ${isInView ? "opacity-100 translate-y-0" : "opacity-0 translate-y-10"}`}>
            Jednostavno kao 1-2-3
          </h2>
          <p className={`text-xl text-gray-500 max-w-2xl mx-auto transition-all duration-700 delay-200 ${isInView ? "opacity-100 translate-y-0" : "opacity-0 translate-y-10"}`}>
            Od gomile papira do strukturiranih podataka za par minuta
          </p>
        </div>

        <div className={`grid lg:grid-cols-2 gap-12 lg:gap-20 items-center transition-all duration-700 delay-300 ${isInView ? "opacity-100 translate-y-0" : "opacity-0 translate-y-20"}`}>

          {/* Left side - Interactive demo */}
          <div className="relative order-2 lg:order-1">
            <div className="relative bg-white rounded-3xl shadow-2xl shadow-violet-200/50 p-6 lg:p-8 border border-gray-100">
              {/* Process visualization */}
              <div className="relative aspect-[4/3] bg-gradient-to-br from-gray-50 to-gray-100 rounded-2xl overflow-hidden">

                {/* Step 1: Upload visualization */}
                <div className={`absolute inset-0 p-4 transition-all duration-500 ${activeStep === 0 ? "opacity-100 scale-100" : "opacity-0 scale-95"}`}>
                  {/* Drop zone - full width */}
                  <div className="relative h-full border-2 border-dashed border-violet-300 rounded-2xl bg-gradient-to-br from-violet-50/80 to-indigo-50/50 flex flex-col items-center justify-center overflow-hidden">
                    {/* Scattered floating documents - more organic placement */}
                    <div className="absolute top-[15%] left-[8%] w-12 h-16 bg-white rounded-lg shadow-lg border border-gray-200 animate-float rotate-[-8deg]" style={{ animationDelay: "0ms" }}>
                      <div className="p-2 space-y-1">
                        <div className="h-1.5 w-7 bg-red-300 rounded" />
                        <div className="h-1 w-5 bg-gray-200 rounded" />
                        <div className="h-1 w-6 bg-gray-200 rounded" />
                      </div>
                    </div>
                    <div className="absolute top-[8%] left-[30%] w-10 h-14 bg-white rounded-lg shadow-md border border-gray-200 animate-float rotate-[5deg]" style={{ animationDelay: "150ms" }}>
                      <div className="p-1.5 space-y-1">
                        <div className="h-1 w-5 bg-blue-300 rounded" />
                        <div className="h-1 w-4 bg-gray-200 rounded" />
                      </div>
                    </div>
                    <div className="absolute top-[12%] right-[12%] w-14 h-18 bg-white rounded-lg shadow-lg border border-gray-200 animate-float rotate-[12deg]" style={{ animationDelay: "300ms" }}>
                      <div className="p-2 space-y-1">
                        <div className="h-1.5 w-8 bg-emerald-300 rounded" />
                        <div className="h-1 w-6 bg-gray-200 rounded" />
                        <div className="h-1 w-7 bg-gray-200 rounded" />
                      </div>
                    </div>
                    <div className="absolute top-[35%] left-[5%] w-11 h-15 bg-white rounded-lg shadow-md border border-gray-200 animate-float rotate-[-12deg]" style={{ animationDelay: "450ms" }}>
                      <div className="p-1.5 space-y-1">
                        <div className="h-1 w-6 bg-amber-300 rounded" />
                        <div className="h-1 w-4 bg-gray-200 rounded" />
                      </div>
                    </div>
                    <div className="absolute top-[40%] right-[6%] w-10 h-13 bg-white rounded-lg shadow-md border border-gray-200 animate-float rotate-[8deg]" style={{ animationDelay: "200ms" }}>
                      <div className="p-1.5 space-y-1">
                        <div className="h-1 w-5 bg-violet-300 rounded" />
                        <div className="h-1 w-4 bg-gray-200 rounded" />
                      </div>
                    </div>
                    <div className="absolute bottom-[20%] left-[12%] w-13 h-17 bg-white rounded-lg shadow-lg border border-gray-200 animate-float rotate-[6deg]" style={{ animationDelay: "100ms" }}>
                      <div className="p-2 space-y-1">
                        <div className="h-1.5 w-7 bg-cyan-300 rounded" />
                        <div className="h-1 w-5 bg-gray-200 rounded" />
                        <div className="h-1 w-6 bg-gray-200 rounded" />
                      </div>
                    </div>
                    <div className="absolute bottom-[15%] right-[15%] w-12 h-16 bg-white rounded-lg shadow-lg border border-gray-200 animate-float rotate-[-6deg]" style={{ animationDelay: "350ms" }}>
                      <div className="p-2 space-y-1">
                        <div className="h-1.5 w-6 bg-pink-300 rounded" />
                        <div className="h-1 w-5 bg-gray-200 rounded" />
                      </div>
                    </div>
                    <div className="absolute bottom-[8%] left-[35%] w-9 h-12 bg-white rounded-lg shadow-md border border-gray-200 animate-float rotate-[-3deg]" style={{ animationDelay: "250ms" }}>
                      <div className="p-1.5 space-y-1">
                        <div className="h-1 w-4 bg-orange-300 rounded" />
                        <div className="h-1 w-3 bg-gray-200 rounded" />
                      </div>
                    </div>

                    {/* Center content */}
                    <div className="relative z-10 text-center bg-white/60 backdrop-blur-sm rounded-2xl px-8 py-6 shadow-lg border border-white/50">
                      <div className="w-14 h-14 mx-auto mb-3 bg-gradient-to-br from-violet-500 to-indigo-500 rounded-xl flex items-center justify-center shadow-lg shadow-violet-500/30 animate-bounce-slow">
                        <DocumentIcon className="w-7 h-7 text-white" />
                      </div>
                      <p className="text-sm font-semibold text-gray-700 mb-0.5">Prevucite fakture ovde</p>
                      <p className="text-xs text-gray-500 mb-3">ili kliknite za odabir</p>
                      {/* File formats */}
                      <div className="flex gap-1.5 justify-center">
                        {["PDF", "JPG", "PNG"].map((fmt) => (
                          <span key={fmt} className="px-2 py-0.5 bg-violet-100 text-violet-600 text-[10px] font-medium rounded-full">{fmt}</span>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Step 2: Processing visualization */}
                <div className={`absolute inset-0 p-4 transition-all duration-500 ${activeStep === 1 ? "opacity-100 scale-100" : "opacity-0 scale-95"}`}>
                  <div className="h-full flex flex-col">
                    {/* Main content area */}
                    <div className="flex-1 flex gap-3 items-stretch">
                      {/* Left: Document being scanned - styled as real invoice */}
                      <div className="w-[38%] relative bg-white rounded-xl shadow-lg border border-gray-200 overflow-hidden">
                        {/* Invoice header */}
                        <div className="bg-gradient-to-r from-gray-800 to-gray-700 px-3 py-2">
                          <div className="flex justify-between items-center">
                            <div className="flex items-center gap-2">
                              <div className="w-6 h-6 bg-white/20 rounded flex items-center justify-center">
                                <span className="text-[8px] font-bold text-white">FA</span>
                              </div>
                              <div>
                                <div className="h-1.5 w-14 bg-white/60 rounded" />
                                <div className="h-1 w-10 bg-white/30 rounded mt-0.5" />
                              </div>
                            </div>
                            <div className="text-right">
                              <div className="text-[8px] font-medium text-white/80">FAKTURA</div>
                              <div className="text-[10px] font-bold text-white">#2025-042</div>
                            </div>
                          </div>
                        </div>

                        {/* Invoice body */}
                        <div className="p-2.5 space-y-2">
                          {/* Seller/Buyer info */}
                          <div className="flex gap-2">
                            <div className="flex-1 p-1.5 bg-gray-50 rounded border border-gray-100">
                              <div className="text-[7px] text-gray-400 uppercase mb-0.5">Prodavac</div>
                              <div className="h-1.5 w-full bg-gray-300 rounded mb-0.5" />
                              <div className="h-1 w-3/4 bg-gray-200 rounded" />
                              <div className="mt-1 px-1 py-0.5 bg-violet-100 rounded inline-block">
                                <span className="text-[7px] font-mono text-violet-600">PIB: 123456789</span>
                              </div>
                            </div>
                            <div className="flex-1 p-1.5 bg-gray-50 rounded border border-gray-100">
                              <div className="text-[7px] text-gray-400 uppercase mb-0.5">Kupac</div>
                              <div className="h-1.5 w-full bg-gray-300 rounded mb-0.5" />
                              <div className="h-1 w-2/3 bg-gray-200 rounded" />
                            </div>
                          </div>

                          {/* Items table */}
                          <div className="border border-gray-200 rounded overflow-hidden">
                            <div className="grid grid-cols-4 gap-1 px-1.5 py-1 bg-gray-100 border-b border-gray-200">
                              <div className="text-[6px] font-semibold text-gray-500 col-span-2">OPIS</div>
                              <div className="text-[6px] font-semibold text-gray-500 text-right">KOL.</div>
                              <div className="text-[6px] font-semibold text-gray-500 text-right">CENA</div>
                            </div>
                            {[1, 2].map((_, i) => (
                              <div key={i} className="grid grid-cols-4 gap-1 px-1.5 py-1 border-b border-gray-100 last:border-0">
                                <div className="col-span-2"><div className="h-1 w-full bg-gray-200 rounded" /></div>
                                <div className="text-right"><div className="h-1 w-4 bg-gray-200 rounded ml-auto" /></div>
                                <div className="text-right"><div className="h-1 w-6 bg-gray-200 rounded ml-auto" /></div>
                              </div>
                            ))}
                          </div>

                          {/* Totals */}
                          <div className="flex justify-end">
                            <div className="w-24 space-y-0.5">
                              <div className="flex justify-between text-[7px]">
                                <span className="text-gray-400">Osnovica:</span>
                                <div className="h-1.5 w-10 bg-gray-200 rounded" />
                              </div>
                              <div className="flex justify-between text-[7px]">
                                <span className="text-gray-400">PDV 20%:</span>
                                <div className="h-1.5 w-8 bg-cyan-200 rounded" />
                              </div>
                              <div className="flex justify-between text-[7px] pt-0.5 border-t border-gray-200">
                                <span className="font-semibold text-gray-600">UKUPNO:</span>
                                <div className="h-2 w-12 bg-emerald-300 rounded" />
                              </div>
                            </div>
                          </div>
                        </div>

                        {/* Scanning overlay effect */}
                        <div className="absolute inset-0 bg-gradient-to-b from-violet-500/5 to-transparent pointer-events-none" />
                        {/* Scanning line */}
                        <div className="absolute inset-x-0 h-0.5 bg-gradient-to-r from-transparent via-violet-500 to-transparent animate-scan" style={{ boxShadow: '0 0 8px 2px rgba(139, 92, 246, 0.4)' }} />

                        {/* Highlight boxes appearing on fields */}
                        <div className="absolute top-[72px] left-[12px] w-[60px] h-[14px] border border-violet-400 rounded bg-violet-400/10 animate-pulse" />
                        <div className="absolute bottom-[28px] right-[12px] w-[48px] h-[10px] border border-emerald-400 rounded bg-emerald-400/10 animate-pulse" style={{ animationDelay: '500ms' }} />
                      </div>

                      {/* Center: AI Avatar with connection lines */}
                      <div className="flex-1 flex items-center justify-center relative">
                        {/* Connection lines from document */}
                        <svg className="absolute inset-0 w-full h-full" style={{ zIndex: 0 }}>
                          <defs>
                            <linearGradient id="lineGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                              <stop offset="0%" stopColor="#8b5cf6" stopOpacity="0.3" />
                              <stop offset="50%" stopColor="#8b5cf6" stopOpacity="0.8" />
                              <stop offset="100%" stopColor="#8b5cf6" stopOpacity="0.3" />
                            </linearGradient>
                          </defs>
                          {/* Animated data flow lines */}
                          <line x1="0" y1="30%" x2="40%" y2="50%" stroke="url(#lineGradient)" strokeWidth="1.5" strokeDasharray="4 4" className="animate-dash" />
                          <line x1="0" y1="50%" x2="40%" y2="50%" stroke="url(#lineGradient)" strokeWidth="1.5" strokeDasharray="4 4" className="animate-dash" />
                          <line x1="0" y1="70%" x2="40%" y2="50%" stroke="url(#lineGradient)" strokeWidth="1.5" strokeDasharray="4 4" className="animate-dash" />
                          <line x1="60%" y1="50%" x2="100%" y2="20%" stroke="url(#lineGradient)" strokeWidth="1.5" strokeDasharray="4 4" className="animate-dash" />
                          <line x1="60%" y1="50%" x2="100%" y2="40%" stroke="url(#lineGradient)" strokeWidth="1.5" strokeDasharray="4 4" className="animate-dash" />
                          <line x1="60%" y1="50%" x2="100%" y2="60%" stroke="url(#lineGradient)" strokeWidth="1.5" strokeDasharray="4 4" className="animate-dash" />
                          <line x1="60%" y1="50%" x2="100%" y2="80%" stroke="url(#lineGradient)" strokeWidth="1.5" strokeDasharray="4 4" className="animate-dash" />
                        </svg>

                        {/* AI Avatar */}
                        <div className="relative z-10">
                          <AIAvatar className="scale-90" />
                        </div>
                      </div>

                      {/* Right: Extracted fields - styled as data cards */}
                      <div className="w-[32%] flex flex-col gap-1.5 justify-center">
                        {[
                          { label: "PIB", value: "123456789", icon: "🏢", gradient: "from-violet-500 to-indigo-500", bg: "bg-violet-50", border: "border-violet-200" },
                          { label: "Datum", value: "15.01.2025", icon: "📅", gradient: "from-indigo-500 to-blue-500", bg: "bg-indigo-50", border: "border-indigo-200" },
                          { label: "Iznos", value: "45.000 RSD", icon: "💰", gradient: "from-cyan-500 to-teal-500", bg: "bg-cyan-50", border: "border-cyan-200" },
                          { label: "PDV", value: "9.000 RSD", icon: "📊", gradient: "from-emerald-500 to-green-500", bg: "bg-emerald-50", border: "border-emerald-200" },
                        ].map((field, i) => (
                          <div
                            key={i}
                            className={`relative ${field.bg} ${field.border} border rounded-xl p-2 animate-scale-in overflow-hidden group`}
                            style={{ animationDelay: `${i * 150}ms` }}
                          >
                            {/* Gradient accent line */}
                            <div className={`absolute left-0 top-0 bottom-0 w-1 bg-gradient-to-b ${field.gradient} rounded-l-xl`} />

                            <div className="flex items-center gap-2 pl-2">
                              <span className="text-sm">{field.icon}</span>
                              <div className="flex-1 min-w-0">
                                <div className="text-[8px] text-gray-400 uppercase tracking-wide">{field.label}</div>
                                <div className="text-[11px] font-mono font-bold text-gray-800 truncate">{field.value}</div>
                              </div>
                              <div className="w-4 h-4 rounded-full bg-emerald-500 flex items-center justify-center flex-shrink-0">
                                <CheckIcon className="w-2.5 h-2.5 text-white" />
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Status bar */}
                    <div className="mt-2 flex items-center justify-between px-3 py-2 bg-white/90 backdrop-blur rounded-xl border border-violet-200 shadow-sm">
                      <div className="flex items-center gap-2">
                        <div className="w-2 h-2 bg-violet-500 rounded-full animate-pulse" />
                        <span className="text-xs font-medium text-violet-600">AI obrađuje dokument...</span>
                      </div>
                      {/* Progress bar */}
                      <div className="flex items-center gap-2">
                        <div className="w-24 h-1.5 bg-gray-200 rounded-full overflow-hidden">
                          <div className="h-full w-2/3 bg-gradient-to-r from-violet-500 to-indigo-500 rounded-full animate-pulse" />
                        </div>
                        <span className="text-xs font-medium text-gray-600">67%</span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Step 3: Export visualization */}
                <div className={`absolute inset-0 p-6 transition-all duration-500 ${activeStep === 2 ? "opacity-100 scale-100" : "opacity-0 scale-95"}`}>
                  <div className="h-full flex flex-col">
                    {/* Header */}
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-2">
                        <div className="w-6 h-6 bg-emerald-500 rounded-full flex items-center justify-center">
                          <CheckIcon className="w-3.5 h-3.5 text-white" />
                        </div>
                        <span className="text-sm font-medium text-gray-700">Podaci spremni</span>
                      </div>
                      <span className="text-xs text-emerald-600 font-medium">3 fakture</span>
                    </div>

                    {/* Data table */}
                    <div className="flex-1 bg-white rounded-xl border border-gray-200 overflow-hidden">
                      {/* Table header */}
                      <div className="grid grid-cols-4 gap-2 px-3 py-2 bg-gray-50 border-b border-gray-200">
                        {["PIB", "Dobavljač", "Iznos", "PDV"].map((h) => (
                          <div key={h} className="text-[10px] font-semibold text-gray-500 uppercase">{h}</div>
                        ))}
                      </div>
                      {/* Table rows */}
                      {[
                        { pib: "123456789", name: "Firma A", amount: "45.000", pdv: "9.000" },
                        { pib: "987654321", name: "Firma B", amount: "28.500", pdv: "5.700" },
                        { pib: "456789123", name: "Firma C", amount: "12.800", pdv: "2.560" },
                      ].map((row, i) => (
                        <div key={i} className="grid grid-cols-4 gap-2 px-3 py-2 border-b border-gray-100 last:border-0 hover:bg-gray-50">
                          <div className="text-xs font-mono text-gray-700">{row.pib}</div>
                          <div className="text-xs text-gray-600 truncate">{row.name}</div>
                          <div className="text-xs font-medium text-gray-800">{row.amount}</div>
                          <div className="text-xs text-gray-600">{row.pdv}</div>
                        </div>
                      ))}
                    </div>

                    {/* Export buttons */}
                    <div className="flex gap-2 mt-3">
                      {[
                        { format: "XLSX", color: "emerald" },
                        { format: "CSV", color: "violet" },
                        { format: "JSON", color: "indigo" },
                      ].map((btn) => (
                        <button
                          key={btn.format}
                          className={`flex-1 px-3 py-2 bg-${btn.color}-50 hover:bg-${btn.color}-100 border border-${btn.color}-200 rounded-lg text-xs font-medium text-${btn.color}-700 transition-colors`}
                        >
                          .{btn.format.toLowerCase()}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              </div>

              {/* Progress indicator */}
              <div className="flex justify-center gap-2 mt-6">
                {[0, 1, 2].map((step) => (
                  <button
                    key={step}
                    onClick={() => setActiveStep(step)}
                    className={`h-2 rounded-full transition-all duration-300 ${activeStep === step ? "w-8 bg-violet-600" : "w-2 bg-gray-300 hover:bg-gray-400"}`}
                  />
                ))}
              </div>
            </div>

            {/* Floating badge */}
            <div className="absolute -bottom-4 -right-4 px-4 py-2 bg-gradient-to-r from-emerald-500 to-teal-500 text-white text-sm font-medium rounded-full shadow-lg shadow-emerald-500/30 animate-bounce-slow">
              Automatski • Brzo • Tačno
            </div>
          </div>

          {/* Right side - Steps */}
          <div className="space-y-6 order-1 lg:order-2">
            {steps.map((step, i) => (
              <div
                key={i}
                onClick={() => setActiveStep(i)}
                className={`group relative p-6 rounded-2xl cursor-pointer transition-all duration-300 ${
                  activeStep === i
                    ? "bg-white shadow-xl shadow-violet-200/50 border-2 border-violet-200"
                    : "bg-gray-50 hover:bg-white hover:shadow-lg border-2 border-transparent hover:border-gray-200"
                }`}
              >
                {/* Active indicator */}
                <div className={`absolute left-0 top-1/2 -translate-y-1/2 w-1 h-12 rounded-r-full bg-gradient-to-b ${step.gradient} transition-opacity duration-300 ${activeStep === i ? "opacity-100" : "opacity-0"}`} />

                <div className="flex items-start gap-4">
                  <div className={`flex-shrink-0 w-12 h-12 rounded-xl bg-gradient-to-br ${step.gradient} flex items-center justify-center shadow-lg transition-transform duration-300 ${activeStep === i ? "scale-110" : "group-hover:scale-105"}`}>
                    <span className="text-lg font-bold text-white">{step.num}</span>
                  </div>
                  <div className="flex-1">
                    <h3 className={`text-xl font-bold mb-2 transition-colors ${activeStep === i ? "text-violet-600" : "text-gray-900"}`}>
                      {step.title}
                    </h3>
                    <p className="text-gray-600 leading-relaxed">{step.description}</p>
                  </div>
                </div>

                {/* Connector line to next step */}
                {i < 2 && (
                  <div className="absolute left-10 -bottom-6 w-0.5 h-6 bg-gradient-to-b from-gray-300 to-transparent" />
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

// Bento Grid Features
function FeaturesSection() {
  const { ref, isInView } = useInView();

  return (
    <section id="funkcije" className="py-32 bg-gradient-to-b from-violet-50/30 to-white relative overflow-hidden">
      {/* Decorative background */}
      <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-violet-200 to-transparent" />
      <div className="absolute top-40 left-10 w-72 h-72 bg-violet-200 rounded-full filter blur-[100px] opacity-40" />
      <div className="absolute bottom-40 right-10 w-72 h-72 bg-indigo-200 rounded-full filter blur-[100px] opacity-40" />

      <div className="relative max-w-7xl mx-auto px-6">
        <div ref={ref} className="text-center mb-20">
          <div className={`inline-flex items-center gap-2 px-4 py-2 bg-white rounded-full shadow-lg shadow-violet-500/10 border border-violet-100 mb-6 transition-all duration-700 ${isInView ? "opacity-100 translate-y-0" : "opacity-0 translate-y-10"}`}>
            <BoltIcon className="w-4 h-4 text-violet-600" />
            <span className="text-sm font-medium text-violet-600">Funkcije</span>
          </div>
          <h2 className={`text-4xl lg:text-5xl font-bold text-gray-900 mb-6 transition-all duration-700 delay-100 ${isInView ? "opacity-100 translate-y-0" : "opacity-0 translate-y-10"}`}>
            Sve što vam treba
          </h2>
          <p className={`text-xl text-gray-500 max-w-2xl mx-auto transition-all duration-700 delay-200 ${isInView ? "opacity-100 translate-y-0" : "opacity-0 translate-y-10"}`}>
            Napravljeno za specifične potrebe srpskog tržišta
          </p>
        </div>

        {/* Bento Grid */}
        <div className={`grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 transition-all duration-700 delay-300 ${isInView ? "opacity-100 translate-y-0" : "opacity-0 translate-y-10"}`}>
          {/* Large feature card - Serbian Documents */}
          <div className="lg:col-span-2 group relative p-8 rounded-3xl bg-gradient-to-br from-violet-600 to-indigo-600 text-white overflow-hidden hover:shadow-2xl hover:shadow-violet-500/30 transition-all duration-500 hover:-translate-y-1">
            <div className="absolute top-0 right-0 w-64 h-64 bg-white/10 rounded-full filter blur-3xl group-hover:scale-150 transition-transform duration-700" />
            <div className="absolute bottom-0 left-0 w-32 h-32 bg-white/5 rounded-full filter blur-2xl" />

            <div className="relative flex flex-col lg:flex-row lg:items-center gap-8">
              <div className="flex-1">
                <div className="w-14 h-14 bg-white/20 rounded-2xl flex items-center justify-center mb-6 backdrop-blur group-hover:scale-110 group-hover:rotate-3 transition-all duration-300">
                  <DocumentIcon className="w-7 h-7 text-white" />
                </div>
                <h3 className="text-2xl font-bold mb-3">Srpski dokumenti</h3>
                <p className="text-white/80 text-lg leading-relaxed max-w-md">
                  Potpuna podrška za ćirilicu i latinicu. Razumemo sve tipove srpskih faktura, fiskalnih računa i poslovne dokumentacije.
                </p>
              </div>

              {/* Mini illustration - Cyrillic/Latin toggle */}
              <div className="hidden lg:block">
                <div className="relative w-48 h-32">
                  {/* Document mockups */}
                  <div className="absolute top-0 left-0 w-20 h-28 bg-white/20 backdrop-blur rounded-lg p-2 rotate-[-6deg] group-hover:rotate-[-12deg] transition-transform duration-500">
                    <div className="text-[8px] font-bold text-white/90 mb-1">ФАКТУРА</div>
                    <div className="space-y-1">
                      <div className="h-1 w-full bg-white/40 rounded" />
                      <div className="h-1 w-3/4 bg-white/30 rounded" />
                      <div className="h-1 w-1/2 bg-white/30 rounded" />
                    </div>
                    <div className="absolute bottom-2 right-2 text-[6px] font-mono text-white/60">ћирилица</div>
                  </div>
                  <div className="absolute top-2 left-16 w-20 h-28 bg-white/25 backdrop-blur rounded-lg p-2 rotate-[6deg] group-hover:rotate-[12deg] transition-transform duration-500">
                    <div className="text-[8px] font-bold text-white/90 mb-1">FAKTURA</div>
                    <div className="space-y-1">
                      <div className="h-1 w-full bg-white/40 rounded" />
                      <div className="h-1 w-2/3 bg-white/30 rounded" />
                      <div className="h-1 w-4/5 bg-white/30 rounded" />
                    </div>
                    <div className="absolute bottom-2 right-2 text-[6px] font-mono text-white/60">latinica</div>
                  </div>
                  {/* Checkmark overlay */}
                  <div className="absolute -bottom-2 right-4 w-10 h-10 bg-emerald-500 rounded-full flex items-center justify-center shadow-lg animate-bounce-slow">
                    <CheckIcon className="w-5 h-5 text-white" />
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* PIB Verification Card */}
          <div className="group relative p-8 rounded-3xl bg-white border border-gray-200/80 shadow-lg shadow-gray-300/30 hover:border-emerald-200 hover:shadow-2xl hover:shadow-emerald-200/30 transition-all duration-500 hover:-translate-y-1 overflow-hidden">
            <div className="absolute top-0 right-0 w-32 h-32 bg-emerald-100 rounded-full filter blur-3xl opacity-0 group-hover:opacity-50 transition-opacity duration-500" />
            <div className="relative">
              <div className="w-14 h-14 bg-emerald-100 rounded-2xl flex items-center justify-center mb-6 group-hover:scale-110 group-hover:rotate-3 transition-all duration-300">
                <CheckCircleIcon className="w-7 h-7 text-emerald-600" />
              </div>
              <h3 className="text-xl font-bold text-gray-900 mb-2 group-hover:text-emerald-600 transition-colors">PIB verifikacija</h3>
              <p className="text-gray-600 mb-4">Automatska provera PIB-a kroz APR bazu podataka.</p>
              {/* Mini PIB check visualization */}
              <div className="flex items-center gap-2 p-2 bg-emerald-50 rounded-lg border border-emerald-100">
                <div className="font-mono text-sm text-gray-600">123456789</div>
                <ArrowRightIcon className="w-4 h-4 text-emerald-500" />
                <div className="flex items-center gap-1 text-emerald-600 text-sm font-medium">
                  <CheckIcon className="w-4 h-4" />
                  Validan
                </div>
              </div>
            </div>
          </div>

          {/* Batch Processing Card */}
          <div className="group relative p-8 rounded-3xl bg-white border border-gray-200/80 shadow-lg shadow-gray-300/30 hover:border-amber-200 hover:shadow-2xl hover:shadow-amber-200/30 transition-all duration-500 hover:-translate-y-1 overflow-hidden">
            <div className="absolute top-0 right-0 w-32 h-32 bg-amber-100 rounded-full filter blur-3xl opacity-0 group-hover:opacity-50 transition-opacity duration-500" />
            <div className="relative">
              <div className="w-14 h-14 bg-amber-100 rounded-2xl flex items-center justify-center mb-6 group-hover:scale-110 group-hover:rotate-3 transition-all duration-300">
                <BoltIcon className="w-7 h-7 text-amber-600" />
              </div>
              <h3 className="text-xl font-bold text-gray-900 mb-2 group-hover:text-amber-600 transition-colors">Batch obrada</h3>
              <p className="text-gray-600 mb-4">Učitajte stotine faktura odjednom. Mi radimo dok vi radite drugo.</p>
              {/* Mini batch visualization */}
              <div className="flex items-end gap-1">
                {[40, 65, 45, 80, 55, 70, 90].map((h, i) => (
                  <div
                    key={i}
                    className="w-4 bg-gradient-to-t from-amber-500 to-amber-300 rounded-t group-hover:animate-pulse"
                    style={{ height: `${h * 0.4}px`, animationDelay: `${i * 100}ms` }}
                  />
                ))}
                <span className="ml-2 text-xs text-gray-500">500+/dan</span>
              </div>
            </div>
          </div>

          {/* All Formats Card */}
          <div className="group relative p-8 rounded-3xl bg-white border border-gray-200/80 shadow-lg shadow-gray-300/30 hover:border-sky-200 hover:shadow-2xl hover:shadow-sky-200/30 transition-all duration-500 hover:-translate-y-1 overflow-hidden">
            <div className="absolute top-0 right-0 w-32 h-32 bg-sky-100 rounded-full filter blur-3xl opacity-0 group-hover:opacity-50 transition-opacity duration-500" />
            <div className="relative">
              <div className="w-14 h-14 bg-sky-100 rounded-2xl flex items-center justify-center mb-6 group-hover:scale-110 group-hover:rotate-3 transition-all duration-300">
                <SparklesIcon className="w-7 h-7 text-sky-600" />
              </div>
              <h3 className="text-xl font-bold text-gray-900 mb-2 group-hover:text-sky-600 transition-colors">Svi formati</h3>
              <p className="text-gray-600 mb-4">PDF, JPEG, PNG, skenovi — podržavamo sve što imate.</p>
              {/* Format badges */}
              <div className="flex flex-wrap gap-2">
                {["PDF", "JPG", "PNG", "TIFF", "SCAN"].map((fmt) => (
                  <span key={fmt} className="px-2 py-1 bg-sky-50 text-sky-600 text-xs font-medium rounded-md border border-sky-100 group-hover:bg-sky-100 transition-colors">
                    {fmt}
                  </span>
                ))}
              </div>
            </div>
          </div>

          {/* Security Card */}
          <div className="group relative p-8 rounded-3xl bg-white border border-gray-200/80 shadow-lg shadow-gray-300/30 hover:border-rose-200 hover:shadow-2xl hover:shadow-rose-200/30 transition-all duration-500 hover:-translate-y-1 overflow-hidden">
            <div className="absolute top-0 right-0 w-32 h-32 bg-rose-100 rounded-full filter blur-3xl opacity-0 group-hover:opacity-50 transition-opacity duration-500" />
            <div className="relative">
              <div className="w-14 h-14 bg-rose-100 rounded-2xl flex items-center justify-center mb-6 group-hover:scale-110 group-hover:rotate-3 transition-all duration-300">
                <ShieldCheckIcon className="w-7 h-7 text-rose-600" />
              </div>
              <h3 className="text-xl font-bold text-gray-900 mb-2 group-hover:text-rose-600 transition-colors">Sigurnost</h3>
              <p className="text-gray-600 mb-4">End-to-end enkripcija. GDPR usklađeno. Vaši podaci su sigurni.</p>
              {/* Security badges */}
              <div className="flex gap-2">
                <div className="flex items-center gap-1 px-2 py-1 bg-rose-50 rounded-md border border-rose-100">
                  <div className="w-2 h-2 bg-emerald-500 rounded-full" />
                  <span className="text-xs font-medium text-gray-600">SSL</span>
                </div>
                <div className="flex items-center gap-1 px-2 py-1 bg-rose-50 rounded-md border border-rose-100">
                  <span className="text-xs font-medium text-gray-600">GDPR</span>
                </div>
                <div className="flex items-center gap-1 px-2 py-1 bg-rose-50 rounded-md border border-rose-100">
                  <span className="text-xs font-medium text-gray-600">AES-256</span>
                </div>
              </div>
            </div>
          </div>

          {/* Full width card - Export */}
          <div className="md:col-span-2 lg:col-span-3 group relative p-8 lg:p-10 rounded-3xl bg-gradient-to-br from-gray-900 to-gray-800 text-white overflow-hidden hover:shadow-2xl hover:shadow-gray-900/30 transition-all duration-500 hover:-translate-y-1">
            <div className="absolute top-0 right-0 w-64 h-64 bg-violet-500/20 rounded-full filter blur-[100px]" />
            <div className="absolute bottom-0 left-1/4 w-48 h-48 bg-emerald-500/10 rounded-full filter blur-[80px]" />
            <div className="absolute top-1/2 right-1/4 w-32 h-32 bg-indigo-500/10 rounded-full filter blur-[60px]" />

            <div className="relative">
              {/* Header */}
              <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6 mb-8">
                <div className="flex items-center gap-4">
                  <div className="w-14 h-14 bg-white/10 rounded-2xl flex items-center justify-center backdrop-blur group-hover:scale-110 group-hover:rotate-3 transition-all duration-300">
                    <TableCellsIcon className="w-7 h-7 text-white" />
                  </div>
                  <div>
                    <h3 className="text-2xl font-bold">Export u bilo kom formatu</h3>
                    <p className="text-gray-400">Direktan uvoz u računovodstveni softver</p>
                  </div>
                </div>
              </div>

              {/* Export format cards - horizontal layout */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {[
                  { format: "XLSX", label: "Excel", desc: "Najpopularniji format za tabelarne podatke", icon: "📊", gradient: "from-emerald-500 to-teal-500" },
                  { format: "CSV", label: "CSV", desc: "Univerzalni format za sve sisteme", icon: "📄", gradient: "from-violet-500 to-indigo-500" },
                  { format: "JSON", label: "JSON", desc: "Za direktnu API integraciju", icon: "{ }", gradient: "from-amber-500 to-orange-500" },
                ].map((item) => (
                  <div
                    key={item.format}
                    className="group/card relative p-5 bg-white/5 hover:bg-white/10 border border-white/10 hover:border-white/20 rounded-2xl backdrop-blur transition-all duration-300 cursor-default"
                  >
                    {/* Gradient accent on hover */}
                    <div className={`absolute inset-0 bg-gradient-to-br ${item.gradient} opacity-0 group-hover/card:opacity-10 rounded-2xl transition-opacity duration-300`} />

                    <div className="relative flex items-start gap-4">
                      <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${item.gradient} flex items-center justify-center text-xl shadow-lg`}>
                        {item.icon}
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="font-mono text-sm text-white/60">.{item.format.toLowerCase()}</span>
                          <span className="text-lg font-bold text-white">{item.label}</span>
                        </div>
                        <p className="text-sm text-gray-400">{item.desc}</p>
                      </div>
                      <ArrowRightIcon className="w-5 h-5 text-gray-500 group-hover/card:text-white group-hover/card:translate-x-1 transition-all mt-1" />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

// Modern Pricing
function PricingSection() {
  const { ref, isInView } = useInView();
  const [annual, setAnnual] = useState(true);

  const plans = [
    {
      name: "Starter",
      description: "Za samostalne računovođe",
      price: annual ? 24 : 29,
      monthlyPrice: 29,
      period: annual ? "/mesec, plaćeno godišnje" : "/mesec",
      features: [
        "100 faktura mesečno",
        "2 korisnika",
        "OCR obrada",
        "Excel/CSV/JSON izvoz",
        "MiniMax XML izvoz",
        "NBS kursna lista",
      ],
      overage: "Prekoračenje: €0,10 po fakturi",
      cta: "Započni besplatno",
      popular: false,
      icon: "🚀",
      color: "violet",
    },
    {
      name: "Pro",
      description: "Za računovodstvene agencije",
      price: annual ? 66 : 79,
      monthlyPrice: 79,
      period: annual ? "/mesec, plaćeno godišnje" : "/mesec",
      features: [
        "400 faktura mesečno",
        "5 korisnika",
        "OCR obrada",
        "Svi formati izvoza",
        "Računovodstvena klasifikacija",
        "SEF integracija",
        "MiniMax direktan uvoz",
        "NBS kursna lista",
      ],
      overage: "Prekoračenje: €0,07 po fakturi",
      cta: "Započni besplatno",
      popular: true,
      icon: "⭐",
      color: "indigo",
    },
    {
      name: "Agency",
      description: "Za velike agencije",
      price: annual ? 165 : 199,
      monthlyPrice: 199,
      period: annual ? "/mesec, plaćeno godišnje" : "/mesec",
      features: [
        "1.500 faktura mesečno",
        "15 korisnika",
        "Sve Pro funkcionalnosti",
        "Pravila automatizacije",
        "Revizijski izvoz",
        "Prioritetna podrška",
      ],
      overage: "Prekoračenje: €0,05 po fakturi",
      cta: "Započni besplatno",
      popular: false,
      icon: "🏢",
      color: "gray",
    },
  ];

  return (
    <section id="cene" className="py-32 bg-gradient-to-b from-white to-gray-50 relative overflow-hidden">
      {/* Decorative elements */}
      <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-gray-200 to-transparent" />
      <div className="absolute top-40 left-10 w-72 h-72 bg-violet-100 rounded-full filter blur-[100px] opacity-50" />
      <div className="absolute bottom-40 right-10 w-72 h-72 bg-indigo-100 rounded-full filter blur-[100px] opacity-50" />

      <div className="relative max-w-7xl mx-auto px-6">
        <div ref={ref} className="text-center mb-16">
          <div className={`inline-flex items-center gap-2 px-4 py-2 bg-violet-50 rounded-full mb-6 transition-all duration-700 ${isInView ? "opacity-100 translate-y-0" : "opacity-0 translate-y-10"}`}>
            <span className="text-sm font-medium text-violet-600">Cene</span>
          </div>
          <h2 className={`text-4xl lg:text-5xl font-bold text-gray-900 mb-6 transition-all duration-700 delay-100 ${isInView ? "opacity-100 translate-y-0" : "opacity-0 translate-y-10"}`}>
            Jednostavne, transparentne cene
          </h2>
          <p className={`text-xl text-gray-500 max-w-2xl mx-auto mb-10 transition-all duration-700 delay-200 ${isInView ? "opacity-100 translate-y-0" : "opacity-0 translate-y-10"}`}>
            Bez skrivenih troškova. Otkažite kada želite.
          </p>

          {/* Toggle */}
          <div className={`inline-flex items-center gap-1 p-1.5 bg-gray-100 rounded-full transition-all duration-700 delay-300 ${isInView ? "opacity-100 translate-y-0" : "opacity-0 translate-y-10"}`}>
            <button
              onClick={() => setAnnual(false)}
              className={`px-6 py-2.5 rounded-full text-sm font-medium transition-all duration-300 ${!annual ? "bg-white shadow-md text-gray-900" : "text-gray-500 hover:text-gray-700"}`}
            >
              Mesečno
            </button>
            <button
              onClick={() => setAnnual(true)}
              className={`px-6 py-2.5 rounded-full text-sm font-medium transition-all duration-300 flex items-center gap-2 ${annual ? "bg-white shadow-md text-gray-900" : "text-gray-500 hover:text-gray-700"}`}
            >
              Godišnje
              <span className="px-2 py-0.5 bg-emerald-100 text-emerald-700 text-xs font-semibold rounded-full">-17%</span>
            </button>
          </div>
        </div>

        <div className={`grid lg:grid-cols-3 gap-6 lg:gap-8 items-start transition-all duration-700 delay-400 ${isInView ? "opacity-100 translate-y-0" : "opacity-0 translate-y-10"}`}>
          {plans.map((plan, i) => (
            <div
              key={i}
              className={`group relative p-8 rounded-3xl transition-all duration-500 hover:-translate-y-2 ${
                plan.popular
                  ? "bg-gradient-to-br from-gray-900 to-gray-800 text-white lg:scale-105 shadow-2xl shadow-violet-500/20 hover:shadow-violet-500/30 z-10"
                  : "bg-white border border-gray-200/80 shadow-lg shadow-gray-200/50 hover:border-violet-200 hover:shadow-2xl hover:shadow-violet-200/30"
              }`}
              style={{ transitionDelay: `${i * 100}ms` }}
            >
              {/* Glow effect for popular plan */}
              {plan.popular && (
                <div className="absolute -inset-px rounded-3xl bg-gradient-to-br from-violet-500 to-indigo-500 opacity-20 blur-xl group-hover:opacity-30 transition-opacity" />
              )}

              {plan.popular && (
                <div className="absolute -top-4 left-1/2 -translate-x-1/2 px-4 py-1.5 bg-gradient-to-r from-violet-500 to-indigo-500 text-white text-xs font-semibold rounded-full shadow-lg shadow-violet-500/30">
                  Najpopularnije
                </div>
              )}

              <div className="relative">
                {/* Icon and name */}
                <div className="flex items-center gap-3 mb-4">
                  <div className={`w-12 h-12 rounded-2xl flex items-center justify-center text-2xl ${
                    plan.popular ? "bg-white/10" : "bg-gray-100"
                  }`}>
                    {plan.icon}
                  </div>
                  <div>
                    <h3 className={`text-xl font-bold ${plan.popular ? "text-white" : "text-gray-900"}`}>{plan.name}</h3>
                    <p className={`text-sm ${plan.popular ? "text-gray-400" : "text-gray-500"}`}>{plan.description}</p>
                  </div>
                </div>

                {/* Price */}
                <div className="mb-6 pb-6 border-b border-gray-200/20">
                  <div className="flex items-baseline gap-1">
                    <span className={`text-5xl font-bold ${plan.popular ? "text-white" : "text-gray-900"}`}>€{plan.price}</span>
                    <span className={`text-sm ${plan.popular ? "text-gray-400" : "text-gray-500"}`}>{plan.period}</span>
                  </div>
                  {annual && (
                    <p className={`text-sm mt-2 ${plan.popular ? "text-emerald-400" : "text-emerald-600"}`}>
                      Ušteda €{(plan.monthlyPrice - plan.price) * 12}/godišnje
                    </p>
                  )}
                </div>

                {/* Features */}
                <ul className="space-y-3 mb-8">
                  {plan.features.map((feature, j) => (
                    <li key={j} className="flex items-center gap-3">
                      <div className={`w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0 ${plan.popular ? "bg-violet-500/20" : "bg-emerald-100"}`}>
                        <CheckIcon className={`w-3 h-3 ${plan.popular ? "text-violet-300" : "text-emerald-600"}`} />
                      </div>
                      <span className={`text-sm ${plan.popular ? "text-gray-300" : "text-gray-600"}`}>{feature}</span>
                    </li>
                  ))}
                </ul>

                {/* Overage info */}
                {plan.overage && (
                  <p className={`text-xs mb-6 ${plan.popular ? "text-gray-500" : "text-gray-400"}`}>
                    {plan.overage}
                  </p>
                )}

                {/* CTA Button */}
                <a
                  href="#kontakt"
                  className={`relative flex items-center justify-center gap-2 w-full py-4 text-center font-medium rounded-full transition-all duration-300 overflow-hidden ${
                    plan.popular
                      ? "bg-white text-gray-900 hover:bg-gray-100 hover:shadow-lg"
                      : "bg-gradient-to-r from-violet-600 to-indigo-600 text-white hover:shadow-xl hover:shadow-violet-500/30 hover:scale-[1.02]"
                  }`}
                >
                  {plan.cta}
                  <ArrowRightIcon className="w-4 h-4" />
                </a>

                {/* Trial note */}
                <p className={`text-center text-xs mt-4 ${plan.popular ? "text-gray-500" : "text-gray-400"}`}>
                  30 dana besplatno • Bez kartice
                </p>
              </div>
            </div>
          ))}
        </div>

        {/* Trust indicators */}
        <div className={`mt-16 text-center transition-all duration-700 delay-500 ${isInView ? "opacity-100 translate-y-0" : "opacity-0 translate-y-10"}`}>
          <p className="text-sm text-gray-500 mb-4">Pouzdano koriste računovođe širom Srbije</p>
          <div className="flex items-center justify-center gap-8 flex-wrap">
            {["🔒 SSL zaštita", "💳 Sigurno plaćanje", "📞 24/7 podrška", "🔄 Otkaži bilo kada"].map((item, i) => (
              <span key={i} className="text-sm text-gray-600 flex items-center gap-1">
                {item}
              </span>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

// CTA Section
function CTASection() {
  const { ref, isInView } = useInView();
  const [email, setEmail] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [focused, setFocused] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    console.log("Email:", email);
    setSubmitted(true);
  };

  return (
    <section id="kontakt" className="py-32 bg-gradient-to-b from-gray-50 to-violet-50/50 relative overflow-hidden">
      {/* Background decoration */}
      <div className="absolute inset-0">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-gradient-to-br from-violet-200 via-indigo-200 to-cyan-200 rounded-full filter blur-[150px] opacity-50 animate-pulse-slow" />
      </div>

      {/* Floating decorative documents */}
      <div className="absolute top-20 left-10 w-16 h-20 bg-white rounded-lg shadow-lg border border-gray-100 rotate-[-12deg] animate-float opacity-60 hidden lg:block">
        <div className="p-2">
          <div className="h-1 w-6 bg-violet-300 rounded mb-1" />
          <div className="h-0.5 w-full bg-gray-200 rounded mb-0.5" />
          <div className="h-0.5 w-3/4 bg-gray-200 rounded" />
        </div>
      </div>
      <div className="absolute top-32 right-16 w-14 h-18 bg-white rounded-lg shadow-lg border border-gray-100 rotate-[8deg] animate-float-delayed opacity-60 hidden lg:block">
        <div className="p-2">
          <div className="h-1 w-5 bg-indigo-300 rounded mb-1" />
          <div className="h-0.5 w-full bg-gray-200 rounded mb-0.5" />
          <div className="h-0.5 w-2/3 bg-gray-200 rounded" />
        </div>
      </div>
      <div className="absolute bottom-24 left-20 w-12 h-16 bg-white rounded-lg shadow-lg border border-gray-100 rotate-[15deg] animate-float opacity-50 hidden lg:block" style={{ animationDelay: "1s" }}>
        <div className="p-1.5">
          <div className="h-0.5 w-4 bg-emerald-300 rounded mb-1" />
          <div className="h-0.5 w-full bg-gray-200 rounded" />
        </div>
      </div>
      <div className="absolute bottom-32 right-24 w-14 h-18 bg-white rounded-lg shadow-lg border border-gray-100 rotate-[-6deg] animate-float-delayed opacity-50 hidden lg:block" style={{ animationDelay: "0.5s" }}>
        <div className="p-2">
          <div className="h-1 w-5 bg-cyan-300 rounded mb-1" />
          <div className="h-0.5 w-full bg-gray-200 rounded" />
        </div>
      </div>

      <div className="relative max-w-5xl mx-auto px-6">
        <div ref={ref} className={`relative bg-white rounded-[2.5rem] p-10 lg:p-16 shadow-2xl shadow-violet-200/50 border border-violet-100/50 transition-all duration-700 ${isInView ? "opacity-100 translate-y-0" : "opacity-0 translate-y-10"}`}>
          {/* Corner decorations */}
          <div className="absolute -top-3 -left-3 w-6 h-6 border-t-2 border-l-2 border-violet-300 rounded-tl-lg" />
          <div className="absolute -top-3 -right-3 w-6 h-6 border-t-2 border-r-2 border-violet-300 rounded-tr-lg" />
          <div className="absolute -bottom-3 -left-3 w-6 h-6 border-b-2 border-l-2 border-violet-300 rounded-bl-lg" />
          <div className="absolute -bottom-3 -right-3 w-6 h-6 border-b-2 border-r-2 border-violet-300 rounded-br-lg" />

          {/* Glow effect */}
          <div className="absolute -inset-px rounded-[2.5rem] bg-gradient-to-br from-violet-500 to-indigo-500 opacity-0 hover:opacity-5 blur-xl transition-opacity duration-500" />

          {!submitted ? (
            <div className="flex flex-col lg:flex-row items-center gap-10 lg:gap-16">
              {/* Left side - Visual illustration */}
              <div className="hidden lg:block flex-shrink-0 relative">
                <div className="relative w-48 h-48">
                  {/* Main circle */}
                  <div className="absolute inset-0 bg-gradient-to-br from-violet-100 to-indigo-100 rounded-full" />

                  {/* AI Avatar in center */}
                  <div className="absolute inset-0 flex items-center justify-center">
                    <div className="relative">
                      <div className="w-20 h-20 bg-gradient-to-br from-violet-600 to-indigo-600 rounded-2xl flex items-center justify-center shadow-lg shadow-violet-500/30 rotate-3">
                        <DocumentIcon className="w-10 h-10 text-white" />
                      </div>
                      {/* Orbiting elements */}
                      <div className="absolute -top-4 -right-4 w-8 h-8 bg-white rounded-lg shadow-md flex items-center justify-center animate-bounce-slow">
                        <span className="text-sm">📊</span>
                      </div>
                      <div className="absolute -bottom-3 -left-5 w-8 h-8 bg-white rounded-lg shadow-md flex items-center justify-center animate-bounce-slow" style={{ animationDelay: "0.3s" }}>
                        <span className="text-sm">✓</span>
                      </div>
                      <div className="absolute top-1/2 -right-8 w-8 h-8 bg-white rounded-lg shadow-md flex items-center justify-center animate-bounce-slow" style={{ animationDelay: "0.6s" }}>
                        <span className="text-sm">⚡</span>
                      </div>
                    </div>
                  </div>

                  {/* Rotating ring */}
                  <div className="absolute inset-2 border-2 border-dashed border-violet-200 rounded-full animate-spin-slow" />
                </div>
              </div>

              {/* Right side - Form */}
              <div className="flex-1 text-center lg:text-left">
                <div className="inline-flex items-center gap-2 px-4 py-2 bg-violet-50 rounded-full mb-6">
                  <SparklesIcon className="w-4 h-4 text-violet-600" />
                  <span className="text-sm font-medium text-violet-600">Rani pristup</span>
                </div>
                <h2 className="text-3xl lg:text-4xl font-bold text-gray-900 mb-4">
                  Spremni da uštedite vreme?
                </h2>
                <p className="text-lg text-gray-500 mb-8">
                  Prijavite se za rani pristup. 30 dana besplatno, bez kartice.
                </p>

                <form onSubmit={handleSubmit} className="relative">
                  <div className="flex flex-col sm:flex-row gap-3">
                    <div className={`relative flex-1 transition-all duration-300 ${focused ? "scale-[1.02]" : ""}`}>
                      {/* Input glow */}
                      <div className={`absolute -inset-1 bg-gradient-to-r from-violet-500 to-indigo-500 rounded-xl blur transition-opacity duration-300 ${focused ? "opacity-20" : "opacity-0"}`} />
                      <input
                        type="email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        onFocus={() => setFocused(true)}
                        onBlur={() => setFocused(false)}
                        placeholder="vas@email.com"
                        required
                        className="relative w-full px-6 py-4 bg-gray-50 border border-gray-200 rounded-xl text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent transition-all"
                      />
                    </div>
                    <button
                      type="submit"
                      className="group px-8 py-4 bg-gradient-to-r from-violet-600 to-indigo-600 text-white font-medium rounded-xl hover:shadow-xl hover:shadow-violet-500/30 transition-all duration-300 hover:scale-[1.02] flex items-center justify-center gap-2"
                    >
                      Prijavi se
                      <ArrowRightIcon className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                    </button>
                  </div>

                  {/* Trust badges below form */}
                  <div className="flex flex-wrap items-center justify-center lg:justify-start gap-4 mt-6">
                    <div className="flex items-center gap-1.5 text-sm text-gray-500">
                      <CheckCircleIcon className="w-4 h-4 text-emerald-500" />
                      <span>Bez kartice</span>
                    </div>
                    <div className="flex items-center gap-1.5 text-sm text-gray-500">
                      <CheckCircleIcon className="w-4 h-4 text-emerald-500" />
                      <span>30 dana besplatno</span>
                    </div>
                    <div className="flex items-center gap-1.5 text-sm text-gray-500">
                      <CheckCircleIcon className="w-4 h-4 text-emerald-500" />
                      <span>Otkaži bilo kada</span>
                    </div>
                  </div>
                </form>
              </div>
            </div>
          ) : (
            <div className="text-center py-8 relative">
              {/* Confetti-like dots */}
              <div className="absolute inset-0 overflow-hidden pointer-events-none">
                {[...Array(12)].map((_, i) => (
                  <div
                    key={i}
                    className="absolute w-2 h-2 rounded-full animate-scale-in"
                    style={{
                      backgroundColor: ["#8b5cf6", "#6366f1", "#10b981", "#06b6d4"][i % 4],
                      left: `${10 + ((i * 37 + 13) % 80)}%`,
                      top: `${10 + ((i * 53 + 7) % 80)}%`,
                      animationDelay: `${i * 50}ms`,
                      opacity: 0.6,
                    }}
                  />
                ))}
              </div>

              <div className="w-24 h-24 bg-gradient-to-br from-emerald-400 to-teal-500 rounded-2xl flex items-center justify-center mx-auto mb-6 shadow-xl shadow-emerald-500/30 animate-scale-in rotate-3">
                <CheckCircleIcon className="w-12 h-12 text-white" />
              </div>
              <h3 className="text-3xl font-bold text-gray-900 mb-3">Hvala na prijavi!</h3>
              <p className="text-lg text-gray-500 mb-6">Javićemo vam se uskoro sa pristupom.</p>
              <div className="inline-flex items-center gap-2 px-4 py-2 bg-emerald-50 text-emerald-700 rounded-full text-sm font-medium">
                <span className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse" />
                Proverite vaš inbox
              </div>
            </div>
          )}
        </div>

        {/* Bottom social proof */}
        <div className={`mt-10 text-center transition-all duration-700 delay-300 ${isInView ? "opacity-100 translate-y-0" : "opacity-0 translate-y-10"}`}>
          <p className="text-sm text-gray-500 mb-4">Pridružite se 500+ računovođa koje već koriste FakturaAI</p>
          <div className="flex items-center justify-center gap-1">
            {[...Array(5)].map((_, i) => (
              <div
                key={i}
                className="w-10 h-10 rounded-full bg-gradient-to-br from-gray-200 to-gray-300 border-2 border-white shadow-sm -ml-2 first:ml-0 flex items-center justify-center text-xs font-medium text-gray-600"
              >
                {["MJ", "AS", "NK", "DT", "IP"][i]}
              </div>
            ))}
            <div className="ml-3 text-sm text-gray-600">
              <span className="font-semibold text-violet-600">+500</span> korisnika
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

// Footer
function Footer() {
  return (
    <footer className="py-20 bg-gray-900 relative overflow-hidden">
      {/* Decorative gradient */}
      <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-violet-500/50 to-transparent" />
      <div className="absolute top-0 left-1/4 w-96 h-32 bg-violet-600 rounded-full filter blur-[100px] opacity-10" />
      <div className="absolute bottom-0 right-1/4 w-64 h-32 bg-indigo-600 rounded-full filter blur-[100px] opacity-10" />

      {/* Grid pattern overlay */}
      <div className="absolute inset-0 opacity-[0.02]" style={{
        backgroundImage: `url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='1'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")`,
      }} />

      <div className="relative max-w-7xl mx-auto px-6">
        {/* Top section with logo and newsletter */}
        <div className="flex flex-col lg:flex-row justify-between items-start gap-12 mb-16">
          <div className="max-w-sm">
            <div className="mb-6">
              <Image
                src="/logo.png"
                alt="FakturaAI"
                width={160}
                height={107}
                className="brightness-0 invert"
              />
            </div>
            <p className="text-gray-400 text-lg leading-relaxed mb-6">
              AI asistent za automatsku obradu faktura. Napravljeno za računovođe u Srbiji.
            </p>
            {/* Status badge */}
            <div className="inline-flex items-center gap-2 px-4 py-2 bg-emerald-500/10 border border-emerald-500/20 rounded-full">
              <span className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse" />
              <span className="text-sm text-emerald-400 font-medium">Svi sistemi operativni</span>
            </div>
          </div>

          {/* Links grid */}
          <div className="grid grid-cols-2 md:grid-cols-3 gap-10 lg:gap-16">
            <div>
              <h4 className="text-white font-semibold mb-5 flex items-center gap-2">
                <div className="w-1.5 h-1.5 bg-violet-500 rounded-full" />
                Proizvod
              </h4>
              <ul className="space-y-4">
                {[
                  { name: "Funkcije", href: "#funkcije" },
                  { name: "Cene", href: "#cene" },
                  { name: "Kako radi", href: "#kako-radi" },
                  { name: "API dokumentacija", href: "#" },
                ].map((item) => (
                  <li key={item.name}>
                    <a href={item.href} className="text-gray-400 hover:text-white transition-colors duration-200 flex items-center gap-2 group">
                      <ArrowRightIcon className="w-3 h-3 opacity-0 -translate-x-2 group-hover:opacity-100 group-hover:translate-x-0 transition-all" />
                      {item.name}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <h4 className="text-white font-semibold mb-5 flex items-center gap-2">
                <div className="w-1.5 h-1.5 bg-indigo-500 rounded-full" />
                Kompanija
              </h4>
              <ul className="space-y-4">
                {["O nama", "Blog", "Karijere", "Press kit"].map((item) => (
                  <li key={item}>
                    <a href="#" className="text-gray-400 hover:text-white transition-colors duration-200 flex items-center gap-2 group">
                      <ArrowRightIcon className="w-3 h-3 opacity-0 -translate-x-2 group-hover:opacity-100 group-hover:translate-x-0 transition-all" />
                      {item}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <h4 className="text-white font-semibold mb-5 flex items-center gap-2">
                <div className="w-1.5 h-1.5 bg-cyan-500 rounded-full" />
                Kontakt
              </h4>
              <ul className="space-y-4 text-gray-400">
                <li>
                  <a href="mailto:info@fakturaai.rs" className="hover:text-white transition-colors flex items-center gap-2">
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                    </svg>
                    info@fakturaai.rs
                  </a>
                </li>
                <li className="flex items-center gap-2">
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                  </svg>
                  Novi Sad, Srbija
                </li>
              </ul>

              {/* Social links */}
              <div className="mt-6 flex items-center gap-3">
                {[
                  { name: "LinkedIn", icon: (
                    <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24"><path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/></svg>
                  )},
                  { name: "Twitter", icon: (
                    <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>
                  )},
                  { name: "GitHub", icon: (
                    <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24"><path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/></svg>
                  )},
                ].map((social) => (
                  <a
                    key={social.name}
                    href="#"
                    className="w-10 h-10 bg-gray-800 hover:bg-violet-600 rounded-lg flex items-center justify-center text-gray-400 hover:text-white transition-all duration-300"
                    aria-label={social.name}
                  >
                    {social.icon}
                  </a>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Bottom bar */}
        <div className="pt-8 border-t border-gray-800/50">
          <div className="flex flex-col md:flex-row justify-between items-center gap-6">
            <div className="flex flex-col md:flex-row items-center gap-4 md:gap-6">
              <p className="text-gray-500 text-sm">© 2025 FakturaAI. Sva prava zadržana.</p>
              <div className="flex items-center gap-1 text-sm text-gray-600">
                <span>Napravljeno sa</span>
                <span className="text-red-500 animate-pulse">❤</span>
                <span>u Srbiji</span>
              </div>
            </div>
            <div className="flex items-center gap-6">
              <a href="#" className="text-gray-500 hover:text-white text-sm transition-colors flex items-center gap-1.5">
                <ShieldCheckIcon className="w-4 h-4" />
                Uslovi korišćenja
              </a>
              <Link href="/politika-privatnosti" className="text-gray-500 hover:text-white text-sm transition-colors flex items-center gap-1.5">
                <ShieldCheckIcon className="w-4 h-4" />
                Privatnost
              </Link>
            </div>
          </div>
        </div>

        {/* Back to top button */}
        <a
          href="#"
          className="absolute bottom-8 right-8 w-12 h-12 bg-gray-800 hover:bg-violet-600 rounded-xl flex items-center justify-center text-gray-400 hover:text-white transition-all duration-300 shadow-lg hover:shadow-violet-500/20 group"
          aria-label="Nazad na vrh"
        >
          <svg className="w-5 h-5 group-hover:-translate-y-1 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 10l7-7m0 0l7 7m-7-7v18" />
          </svg>
        </a>
      </div>
    </footer>
  );
}

// Main
export default function Home() {
  return (
    <main className="relative">
      <AnimatedBackground />
      <LandingNav />
      <HeroSection />
      <TransformationSection />
      <HowItWorksSection />
      <FeaturesSection />
      <PricingSection />
      <CTASection />
      <Footer />

    </main>
  );
}
