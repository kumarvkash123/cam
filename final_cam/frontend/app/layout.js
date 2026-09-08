import "./globals.css";

export const metadata = {
  title: "CAM AI Platform",
  description: "Bank CAM credit appraisal platform",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
