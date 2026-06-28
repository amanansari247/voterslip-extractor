import "./globals.css";

export const metadata = {
  title: "Voter PDF Cropper",
  description: "Prepare voter slips from PDF crop boxes",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
