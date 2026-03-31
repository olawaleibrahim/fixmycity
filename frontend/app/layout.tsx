import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "FixMyCity — Urban Insight Platform",
  description: "Live urban hazard detection and housing risk analysis.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="h-full">
      <body className={`${inter.className} bg-gray-950 text-gray-100 h-full`}>
        {children}
      </body>
    </html>
  );
}
