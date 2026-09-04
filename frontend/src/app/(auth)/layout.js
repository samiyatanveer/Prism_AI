/**
 * Auth route group layout.
 * Provides server-side metadata for the login/register pages.
 */

export const metadata = {
  title: "Sign In",
  description: "Sign in to your PrismAI account.",
};

export default function AuthLayout({ children }) {
  return children;
}
