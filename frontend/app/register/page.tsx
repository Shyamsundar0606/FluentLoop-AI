"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";

import {
  AuthShell,
  buttonClass,
  FormMessage,
  inputClass,
} from "@/components/auth-shell";
import { apiRequest, getApiErrorMessage } from "@/lib/api";

export default function RegisterPage() {
  const [values, setValues] = useState({
    full_name: "",
    age: "",
    email: "",
    password: "",
    confirm_password: "",
  });
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    if (!values.full_name.trim()) {
      setError("Full name is required.");
      return;
    }
    const age = values.age === "" ? null : Number(values.age);
    if (age !== null && (!Number.isInteger(age) || age < 0 || age > 120)) {
      setError("Enter a whole age between 0 and 120, or leave it blank.");
      return;
    }
    if (
      !/\p{Ll}/u.test(values.password) ||
      !/\p{Lu}/u.test(values.password) ||
      !/\p{Nd}/u.test(values.password) ||
      values.password.trim().length < 12
    ) {
      setError(
        "Password must contain at least 12 characters, uppercase, lowercase, and a number.",
      );
      return;
    }
    if (values.password !== values.confirm_password) {
      setError("Passwords do not match.");
      return;
    }
    setLoading(true);
    try {
      await apiRequest("/auth/register", {
        method: "POST",
        body: JSON.stringify({
          ...values,
          full_name: values.full_name.trim(),
          age,
        }),
      });
      setSuccess(true);
    } catch (reason) {
      setError(
        getApiErrorMessage(reason, "Registration could not be completed."),
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthShell
      title="Create your free account"
      description="Start your French learning journey. No payment details or prior French experience required."
    >
      {success ? (
        <div className="space-y-4">
          <FormMessage>
            Registration received. Check the local inbox at
            http://localhost:8025 to verify your email.
          </FormMessage>
          <Link
            className="text-sm font-semibold text-violet-700 dark:text-violet-300"
            href="/verify-email"
          >
            Continue to email verification
          </Link>
        </div>
      ) : (
        <form className="space-y-4" onSubmit={submit}>
          <label className="block text-sm font-medium">
            Full name
            <input
              className={inputClass}
              required
              maxLength={80}
              autoComplete="name"
              value={values.full_name}
              onChange={(e) =>
                setValues({ ...values, full_name: e.target.value })
              }
            />
          </label>
          <label className="block text-sm font-medium">
            Age (optional)
            <input
              className={inputClass}
              type="number"
              min={0}
              max={120}
              step={1}
              inputMode="numeric"
              aria-describedby="age-privacy"
              value={values.age}
              onChange={(e) => setValues({ ...values, age: e.target.value })}
            />
          </label>
          <p id="age-privacy" className="text-xs text-slate-500">
            You can leave age blank. If provided, we save only whether you were
            under 18 or 18 and over at registration, not your exact age. Age is
            not sent to the AI tutor.
          </p>
          <label className="block text-sm font-medium">
            Email
            <input
              className={inputClass}
              required
              type="email"
              autoComplete="email"
              maxLength={254}
              value={values.email}
              onChange={(e) => setValues({ ...values, email: e.target.value })}
            />
          </label>
          <label className="block text-sm font-medium">
            Password
            <input
              className={inputClass}
              required
              type={showPassword ? "text" : "password"}
              minLength={12}
              maxLength={128}
              autoComplete="new-password"
              value={values.password}
              onChange={(e) =>
                setValues({ ...values, password: e.target.value })
              }
            />
            <span className="mt-1 block text-xs text-slate-500">
              At least 12 characters with uppercase, lowercase, and a number.
            </span>
          </label>
          <label className="block text-sm font-medium">
            Confirm password
            <input
              className={inputClass}
              required
              type={showPassword ? "text" : "password"}
              minLength={12}
              maxLength={128}
              autoComplete="new-password"
              value={values.confirm_password}
              onChange={(e) =>
                setValues({ ...values, confirm_password: e.target.value })
              }
            />
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={showPassword}
              onChange={(e) => setShowPassword(e.target.checked)}
            />
            Show passwords
          </label>
          {error && <FormMessage error>{error}</FormMessage>}
          <button className={buttonClass} disabled={loading}>
            {loading ? "Creating account…" : "Create free account"}
          </button>
          <p className="text-center text-sm text-slate-600 dark:text-slate-300">
            Already registered?{" "}
            <Link
              className="font-semibold text-violet-700 dark:text-violet-300"
              href="/login"
            >
              Sign in
            </Link>
          </p>
        </form>
      )}
    </AuthShell>
  );
}
