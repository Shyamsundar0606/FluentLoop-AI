import Link from "next/link";
import { BackendIndicator } from "@/components/backend-indicator";
import { ThemeToggle } from "@/components/theme-toggle";
import { Icon } from "@/components/ui";

export default function Home() {
  return (
    <main className="landing">
      <header className="landing-nav">
        <Link href="/" className="brand">
          <span className="brand-mark">
            f<span>l</span>
          </span>
          FluentLoop AI
        </Link>
        <div className="flex items-center gap-5">
          <Link className="text-sm" href="/login">
            Sign in
          </Link>
          <Link href="/register" className="button button-primary">
            Get started
          </Link>
        </div>
      </header>
      <section className="landing-hero">
        <p className="eyebrow">Your space to learn French</p>
        <h1>
          A little practice.
          <br />
          <span>A little more French.</span>
        </h1>
        <p>
          Learn at your pace, ask questions freely, and find your voice in
          French. Your lessons and conversations, together in one calm space.
        </p>
        <div className="flex flex-wrap justify-center gap-3">
          <Link href="/register" className="button button-primary">
            Start learning <Icon name="arrow" />
          </Link>
          <Link href="/login" className="button button-secondary">
            Continue your journey
          </Link>
        </div>
      </section>
      <section className="landing-features" aria-label="Ways to practice">
        {[
          {
            icon: "learn" as const,
            title: "Learn with direction",
            text: "Follow French lessons and revisit your saved progress whenever you need.",
          },
          {
            icon: "chat" as const,
            title: "Make room for questions",
            text: "Explore vocabulary, understand grammar and practice with your AI tutor.",
          },
          {
            icon: "mic" as const,
            title: "Say it in French",
            text: "Try a conversation, review what was heard and listen to a French reply.",
          },
        ].map((item) => (
          <article className="panel" key={item.title}>
            <Icon name={item.icon} />
            <h2>{item.title}</h2>
            <p>{item.text}</p>
          </article>
        ))}
      </section>
      <footer className="mt-14 flex flex-wrap items-start justify-between gap-5 border-t border-slate-200 pt-6 text-xs text-slate-500">
        <p>
          FluentLoop AI · French, one conversation at a time.
          <br />
          AI can make mistakes. Reviewed course availability varies by level.
        </p>
        <details>
          <summary>Appearance and service status</summary>
          <ThemeToggle />
          <BackendIndicator />
        </details>
      </footer>
    </main>
  );
}
