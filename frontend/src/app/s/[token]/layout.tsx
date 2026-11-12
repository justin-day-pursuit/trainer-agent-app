/**
 * Client Session Layout & Static Pre-rendering Configuration
 *
 * This layout defines the static parameters for the client session token route `/s/[token]`.
 * During Next.js production build (`next build`), `generateStaticParams` pre-renders the demo
 * client session page (`/s/demo-client-session`), ensuring all client workout logging UI,
 * React components, and static chunks are compiled ahead of time for both automated video
 * recording and fast production delivery.
 */

// Tell Next.js which token paths to pre-render during the build process
export function generateStaticParams() {
  return [{ token: "demo-client-session" }];
}

// Pass-through wrapper layout that renders the active client session page
export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
