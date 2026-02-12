import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { AuthProvider } from "@/contexts/AuthContext";
import "./globals.css";

const inter = Inter({
  subsets: ["latin", "latin-ext"],
  variable: "--font-inter",
});

export const metadata: Metadata = {
  title: "FakturaAI - Automatska obrada faktura | AI za računovođe",
  description:
    "Uštedite 10+ sati mesečno. AI koji čita vaše fakture i automatski izvlači sve podatke. Za računovodstvene agencije u Srbiji.",
  keywords: [
    "fakture",
    "OCR",
    "računovodstvo",
    "automatizacija",
    "AI",
    "Srbija",
    "księgovodstvo",
  ],
  openGraph: {
    title: "FakturaAI - Automatska obrada faktura",
    description: "AI koji čita vaše fakture i automatski izvlači sve podatke.",
    locale: "sr_RS",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="sr" className="scroll-smooth">
      <body className={`${inter.variable} font-sans antialiased`}>
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
