import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "INVOP.ai — Decisiones de negocio con Investigación Operativa + AI",
  description: "Optimizá tu inventario, pronosticá ventas, analizá rentabilidad y proyectá flujo de caja. Conectá tu Shopify y dejá que la AI trabaje por vos.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="es">
      <body className="antialiased">
        {children}
      </body>
    </html>
  );
}
