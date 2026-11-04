import Link from "next/link";

export function AuthShell({
  title,
  description,
  children,
}: {
  title: string;
  description: string;
  children: React.ReactNode;
}) {
  return (
    <main className="auth-page">
      <div className="mx-auto max-w-lg">
        <Link href="/" className="brand">
          <span className="brand-mark">
            f<span>l</span>
          </span>
          FluentLoop AI
        </Link>
        <section className="auth-card">
          <h1 className="text-3xl font-bold tracking-tight">{title}</h1>
          <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">
            {description}
          </p>
          <div className="mt-7">{children}</div>
        </section>
      </div>
    </main>
  );
}

export const inputClass =
  "mt-1 block w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-900 outline-none focus:border-violet-500 focus:ring-2 focus:ring-violet-200 dark:border-slate-700 dark:bg-slate-950 dark:text-white dark:focus:ring-violet-900";

export const buttonClass = "button button-primary w-full";

export function FormMessage({
  children,
  error = false,
}: {
  children: React.ReactNode;
  error?: boolean;
}) {
  return (
    <p
      role={error ? "alert" : "status"}
      className={`rounded-xl px-3 py-2 text-sm ${error ? "bg-rose-50 text-rose-800 dark:bg-rose-950/50 dark:text-rose-200" : "bg-emerald-50 text-emerald-800 dark:bg-emerald-950/50 dark:text-emerald-200"}`}
    >
      {children}
    </p>
  );
}
