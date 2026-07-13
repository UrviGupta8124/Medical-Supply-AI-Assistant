import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Defense Medical RAG",
  description: "Verified medical database query system for defense personnel.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        {children}
      </body>
    </html>
  );
}
