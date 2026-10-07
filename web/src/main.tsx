import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { ThemeProvider } from 'next-themes'

import '@/index.css'
import App from '@/App.tsx'
import { Toaster } from '@/components/ui/sonner'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    {/* React never executes this inline script on the client; index.html applies the initial theme instead. */}
    <ThemeProvider
      attribute="class"
      defaultTheme="system"
      enableSystem
      disableTransitionOnChange
      storageKey="marketmesh-theme"
      scriptProps={{ type: 'application/json' }}
    >
      <App />
      <Toaster richColors closeButton />
    </ThemeProvider>
  </StrictMode>,
)
