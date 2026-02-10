import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Congreso Abierto - Transparencia Parlamentaria',
  description: 'Plataforma ciudadana de transparencia del Congreso argentino',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body>
        <header className="bg-congress-blue text-white px-6 py-4 shadow-md">
          <nav className="max-w-6xl mx-auto flex items-center justify-between">
            <a href="/" className="text-xl font-bold">Congreso Abierto</a>
            <div className="flex gap-6 text-sm">
              <a href="/" className="hover:text-congress-gold transition">Feed</a>
              <a href="/explorer" className="hover:text-congress-gold transition">Explorar</a>
              <a href="/como-funciona" className="hover:text-congress-gold transition">Cómo Funciona</a>
            </div>
          </nav>
        </header>
        <main className="max-w-6xl mx-auto px-4 py-6">{children}</main>
        <footer className="bg-gray-100 text-gray-500 text-center py-4 text-sm mt-12">
          Congreso Abierto — Datos públicos del HCDN. No se emiten opiniones.
        </footer>
      </body>
    </html>
  );
}
