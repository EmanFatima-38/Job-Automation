"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { UserPlus } from "lucide-react";
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
  fullName: z.string().optional(),
  email: z.string().email(),
  password: z.string().min(8, "Password must be at least 8 characters"),
});

type FormValues = z.infer<typeof schema>;

export default function RegisterPage() {
  const { register: registerUser } = useAuth();
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
      await registerUser(values.email, values.password, values.fullName);
      router.push("/dashboard");
    } catch (err) {
      setServerError(err instanceof ApiError ? err.message : "Something went wrong");
    }
  }

  return (
    <AuthLayout title="Create your account" subtitle="Organize and automate your job search.">
      <Card>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <Field label="Full name (optional)">
            <Input placeholder="Jane Doe" {...register("fullName")} />
          </Field>
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
            <UserPlus className="h-4 w-4" />
            {isSubmitting ? "Creating account..." : "Create account"}
          </Button>
        </form>
      </Card>
      <p className="mt-6 text-center text-sm text-zinc-500 dark:text-zinc-400">
        Already have an account?{" "}
        <Link href="/login" className="font-medium text-brand hover:text-brand-dark dark:text-brand-light">
          Log in
        </Link>
      </p>
    </AuthLayout>
  );
}
