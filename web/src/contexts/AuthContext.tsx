import React from "react";
import { onAuth } from "../lib/auth";
import type { User } from "firebase/auth";

interface AuthState {
  user: User | null;
  loading: boolean;
}

const Ctx = React.createContext<AuthState>({ user: null, loading: true });

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = React.useState<AuthState>({
    user: null,
    loading: true,
  });

  React.useEffect(() => {
    return onAuth((user) => setState({ user, loading: false }));
  }, []);

  return <Ctx.Provider value={state}>{children}</Ctx.Provider>;
}

export function useAuth() {
  return React.useContext(Ctx);
}
