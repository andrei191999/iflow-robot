import { useState } from "react";
import { emailPasswordSignIn } from "../lib/auth";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { useNavigate } from "react-router-dom";

export default function SignIn() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const nav = useNavigate();

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await emailPasswordSignIn(email, password);
      nav("/schedules");
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto grid min-h-screen max-w-md place-items-center p-6">
      <form
        onSubmit={onSubmit}
        className="w-full rounded-2xl bg-white p-6 shadow"
      >
        <h1 className="mb-4 text-xl font-semibold">Sign in</h1>
        <div className="space-y-3">
          <div>
            <label className="mb-1 block text-sm">Email</label>
            <Input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>
          <div>
            <label className="mb-1 block text-sm">Password</label>
            <Input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>
          {error && <p className="text-sm text-red-600">{error}</p>}
          <Button type="submit" disabled={loading} className="w-full">
            {loading ? "Signing in…" : "Sign in"}
          </Button>

          <div className="relative my-4">
            <div className="absolute inset-0 flex items-center">
              <span className="w-full border-t" />
            </div>
            <div className="relative flex justify-center text-xs uppercase">
              <span className="bg-white px-2 text-gray-500">Or continue with</span>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <Button
              type="button"
              variant="outline"
              onClick={() => nav("/demo")}
              className="w-full"
            >
              Try Demo
            </Button>
            <Button
              type="button"
              variant="outline"
              onClick={() => nav("/signup")}
              className="w-full"
            >
              Sign Up
            </Button>
          </div>
        </div>
      </form>
    </div>
  );
}
