import { Inter, Playfair_Display } from 'next/font/google';
import './globals.css';
import Sidebar from '@/components/Sidebar';
import TopBar from '@/components/TopBar';
import FloatingChat from '@/components/FloatingChat';


const inter = Inter({
  subsets: ['latin'],
  display: 'swap',
  variable: '--font-inter',
});

const playfair = Playfair_Display({
  subsets: ['latin'],
  display: 'swap',
  weight: ['600', '700', '800'],
  variable: '--font-display',
});

export const metadata = {
  title: 'Atmos - Urban Air Quality Intelligence',
  description: 'AI-powered hyperlocal AQI forecasting for Indian cities',
};

export default function RootLayout({ children }) {
  return (
    <html lang="en" className={`${inter.variable} ${playfair.variable}`}>
      <body className={inter.className}>
        <div className="app-layout">
          <Sidebar />
          <div className="main-area">
            <TopBar />
            <main className="page-content">
              {children}
            </main>
          </div>
        </div>
        <FloatingChat />
      </body>
    </html>
  );
}