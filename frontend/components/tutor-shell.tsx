"use client";
import { ProtectedPage } from "./auth-provider";

export function TutorShell({ children }: { children: React.ReactNode }) {
  return (
    <ProtectedPage>
      <main className="min-h-screen bg-slate-50 p-5 text-slate-900 dark:bg-slate-950 dark:text-slate-100">
        <div className="mx-auto max-w-4xl">
          {children}
          <details className="privacy-note">
            <summary>About your conversations and privacy</summary>
            <p>
              Free text practice. AI can make mistakes; responses are not
              linguistically certified. Messages remain in your account until an
              operator applies the documented retention policy. The configured
              Ollama server processes your messages; ask the deployment operator
              about its location. Avoid sharing sensitive personal details.
            </p>
          </details>
        </div>
      </main>
    </ProtectedPage>
  );
}
