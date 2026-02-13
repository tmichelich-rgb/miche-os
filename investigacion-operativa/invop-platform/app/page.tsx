import { redirect } from 'next/navigation';

// Root page redirects to the SPA (during migration)
// Eventually this will be a proper Next.js landing page
export default function Home() {
  redirect('/legacy/app.html');
}
