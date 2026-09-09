import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "MoveScore — Dance first. Music second.",
  description:
    "Upload your choreography and get original music composed around your movement.",
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
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
