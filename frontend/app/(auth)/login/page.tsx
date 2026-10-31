"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { LogIn } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { ApiError } from "@/lib/api-client";
import { AuthLayout } from "@/components/auth/AuthLayout";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { useAuth } from "@/providers/AuthProvider";

const schema = z.object({
  email: z.string().email(),
  password: z.string().min(1, "Password is required"),
});

type FormValues = z.infer<typeof schema>;

export default function LoginPage() {
  const { login } = useAuth();
  const router = useRouter();
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  async function onSubmit(values: FormValues) {
    setServerError(null);
    try {
      await login(values.email, values.password);
      router.push("/dashboard");
    } catch (err) {
      setServerError(err instanceof ApiError ? err.message : "Something went wrong");
    }
  }

  return (
    <AuthLayout title="Welcome back" subtitle="Log in to keep your search moving.">
      <Card>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <Field label="Email" error={errors.email?.message}>
            <Input type="email" placeholder="you@example.com" {...register("email")} />
          </Field>
          <Field label="Password" error={errors.password?.message}>
            <Input type="password" placeholder="••••••••" {...register("password")} />
          </Field>
          {serverError && (
            <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600 dark:bg-red-950/40 dark:text-red-400">
              {serverError}
            </p>
          )}
          <Button type="submit" disabled={isSubmitting} className="w-full">
            <LogIn className="h-4 w-4" />
            {isSubmitting ? "Logging in..." : "Log in"}
          </Button>
        </form>
      </Card>
      <p className="mt-6 text-center text-sm text-zinc-500 dark:text-zinc-400">
        No account?{" "}
        <Link href="/register" className="font-medium text-brand hover:text-brand-dark dark:text-brand-light">
          Register
        </Link>
      </p>
    </AuthLayout>
  );
}
