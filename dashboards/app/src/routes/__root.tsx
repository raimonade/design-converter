import { createRootRoute, Outlet } from '@tanstack/react-router';
import { useEffect, useState } from 'react';
import { Sidebar } from '@/components/layout/Sidebar';
import { SearchProvider } from '@/context/SearchContext';
import { SearchPalette } from '@/components/dashboard/SearchPalette';

function RootLayout() {
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    const onScroll = () => {
      const scrollTop = window.scrollY;
      const docH = document.documentElement.scrollHeight - window.innerHeight;
      if (docH > 0) setProgress((scrollTop / docH) * 100);
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  return (
    <SearchProvider>
      <div className="flex min-h-screen">
        {/* Progress bar */}
        <div
          className="fixed top-0 left-0 right-0 h-[2px] z-[1000]"
          style={{
            width: `${progress}%`,
            background: 'linear-gradient(90deg, var(--color-accent), #6EE7B7)',
            boxShadow: '0 0 12px var(--color-accent)',
            transition: 'width 0.1s linear',
          }}
        />

        <Sidebar />
        <main className="flex-1 min-w-0" style={{ marginLeft: 'var(--sidebar-width)' }}>
          <Outlet />
        </main>
      </div>

      <SearchPalette />
    </SearchProvider>
  );
}

export const Route = createRootRoute({
  component: RootLayout,
});
