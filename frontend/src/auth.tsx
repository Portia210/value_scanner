import { createContext, useContext, type ReactNode } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError, setCsrf } from "./api/client";

interface Auth { loggedIn: boolean; loading: boolean; login: (password: string) => Promise<void>; logout: () => Promise<void>; }
const AuthContext = createContext<Auth | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const qc = useQueryClient();
  const me = useQuery({
    queryKey: ["me"],
    retry: false,
    queryFn: async () => {
      try {
        const r = await api<{ csrf: string }>("/auth/me");
        setCsrf(r.csrf);
        return true;
      } catch (e) {
        if (e instanceof ApiError && e.status === 401) return false;
        throw e;
      }
    },
  });
  const login = async (password: string) => {
    const r = await api<{ csrf: string }>("/auth/login", { method: "POST", json: { password } });
    setCsrf(r.csrf);
    qc.setQueryData(["me"], true);
  };
  const logout = async () => {
    await api("/auth/logout", { method: "POST" });
    setCsrf("");
    qc.removeQueries({ predicate: (q) => q.queryKey[0] !== "me" }); // keep the "me" observer alive
    qc.setQueryData(["me"], false);
  };
  return (
    <AuthContext.Provider value={{ loggedIn: me.data === true, loading: me.isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): Auth {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth outside AuthProvider");
  return ctx;
}
