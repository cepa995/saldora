import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { NextIntlClientProvider } from "next-intl";
import { getLocale, getMessages } from "next-intl/server";
import { AuthProvider } from "@/contexts/AuthContext";
import "./globals.css";

const inter = Inter({
  subsets: ["latin", "latin-ext", "cyrillic", "cyrillic-ext"],
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
  ],
  openGraph: {
    title: "FakturaAI - Automatska obrada faktura",
    description:
      "AI koji čita vaše fakture i automatski izvlači sve podatke.",
    locale: "sr_RS",
    type: "website",
  },
};

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const locale = await getLocale();
  const messages = await getMessages();

  return (
    <html lang={locale === "en" ? "en" : "sr"} className="scroll-smooth">
      <body className={`${inter.variable} font-sans antialiased`}>
        <NextIntlClientProvider messages={messages}>
          <AuthProvider>{children}</AuthProvider>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
