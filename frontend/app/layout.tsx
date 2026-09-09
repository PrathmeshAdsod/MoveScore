import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-inter",
});

export const metadata: Metadata = {
  title: "MoveScore — Dance first. Music second.",
  description:
    "Upload your choreography and get original AI-composed music built around your movement. Powered by Gemini and Lyria 3.5.",
  openGraph: {
    title: "MoveScore",
    description: "Dance first. Music second.",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={inter.variable}>
      <body>{children}</body>
    </html>
  );
}
