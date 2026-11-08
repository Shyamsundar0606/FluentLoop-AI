"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";
import type { AuthUser } from "./auth-provider";
import { Icon, type IconName } from "./ui";
import { ThemeToggle } from "./theme-toggle";

const destinations: { label: string; href: string; icon: IconName }[] = [
  { label: "Home", href: "/dashboard", icon: "home" },
  { label: "Learn", href: "/courses", icon: "learn" },
  { label: "AI Tutor", href: "/ai-tutor", icon: "chat" },
  { label: "Speak", href: "/voice-practice", icon: "mic" },
  { label: "Profile", href: "/profile", icon: "profile" },
];
const sections: Record<string, { label: string; href: string }[]> = {
  Learn: [
    { label: "French courses", href: "/courses" },
    { label: "Vocabulary", href: "/vocabulary" },
    { label: "Grammar", href: "/grammar" },
    { label: "Progress", href: "/progress" },
  ],
  "AI Tutor": [
    { label: "Chat", href: "/ai-tutor" },
    { label: "Conversation practice", href: "/ai-tutor/scenarios" },
    { label: "History", href: "/ai-tutor/history" },
    { label: "Recommended practice", href: "/ai-tutor/recommendations" },
  ],
  Speak: [
    { label: "Voice Practice", href: "/voice-practice" },
    { label: "Conversations", href: "/voice-practice/conversations" },
    { label: "Pronunciation", href: "/voice-practice/pronunciation" },
    { label: "Speech history", href: "/voice-practice/history" },
  ],
  Profile: [
    { label: "Your profile", href: "/profile" },
    { label: "Settings", href: "/settings" },
    { label: "Learning setup", href: "/onboarding" },
  ],
};
export function AppShell({
  children,
  user,
  onSignOut,
}: {
  children: React.ReactNode;
  user: AuthUser;
  onSignOut: () => Promise<void>;
}) {
  const path = usePathname();
  const router = useRouter();
  const [error, setError] = useState("");
  const section = path.startsWith("/ai-tutor")
    ? "AI Tutor"
    : path.startsWith("/voice-practice")
      ? "Speak"
      : /^(\/profile|\/settings)/.test(path)
        ? "Profile"
        : path === "/dashboard"
          ? "Home"
          : "Learn";
  if (path === "/onboarding") return <>{children}</>;
  const name = user.display_name.trim() || "Learner";
  async function logout() {
    try {
      await onSignOut();
      router.replace("/login");
    } catch {
      setError("Could not sign out. Please try again.");
    }
  }
  return (
    <div className="app-shell">
      <a className="skip-link" href="#page-content">
        Skip to content
      </a>
      <aside className="app-sidebar">
        <Link
          href="/dashboard"
          className="brand"
          aria-label="FluentLoop AI home"
        >
          <span className="brand-mark">
            f<span>l</span>
          </span>
          <span>
            FluentLoop<span className="brand-ai"> AI</span>
          </span>
        </Link>
        <p className="sidebar-caption">A little French, every day.</p>
        <nav aria-label="Main navigation" className="primary-nav">
          {destinations.map((item) => (
            <Link
              key={item.label}
              href={item.href}
              aria-current={section === item.label ? "page" : undefined}
            >
              <Icon name={item.icon} />
              <span>{item.label}</span>
            </Link>
          ))}
        </nav>
        <div className="sidebar-footer">
          <div className="learner-card">
            <span className="avatar" aria-hidden="true">
              {name.charAt(0).toUpperCase()}
            </span>
            <div>
              <p>{name}</p>
              <span>
                French · {user.preferences.current_level.toUpperCase()}
              </span>
            </div>
          </div>
          <button onClick={() => void logout()} className="signout-button">
            Sign out
          </button>
        </div>
      </aside>
      <div className="app-workspace">
        <header className="app-topbar">
          <span className="topbar-title">
            {section === "Home" ? "Your French journey" : section}
          </span>
          <div className="topbar-tools">
            <span className="level-badge">
              French · {user.preferences.current_level.toUpperCase()}
            </span>
            <details className="account-menu">
              <summary aria-label="Account options">
                <span className="avatar" aria-hidden="true">
                  {name.charAt(0).toUpperCase()}
                </span>
              </summary>
              <div>
                <p>{name}</p>
                <Link href="/settings">Preferences</Link>
                <ThemeToggle />
                <button onClick={() => void logout()}>Sign out</button>
              </div>
            </details>
          </div>
        </header>
        {sections[section] && !(section === 'Learn' && ['/courses','/grammar','/practice'].includes(path)) && (
          <nav className="section-nav" aria-label={`${section} sections`}>
            {sections[section].map((item) => (
              <Link
                key={item.href}
                href={item.href}
                aria-current={path === item.href ? "page" : undefined}
              >
                {item.label}
              </Link>
            ))}
          </nav>
        )}
        <div className="app-content" id="page-content" tabIndex={-1}>
          {error && (
            <p role="alert" className="status-error">
              {error}
            </p>
          )}
          {children}
        </div>
      </div>
    </div>
  );
}
