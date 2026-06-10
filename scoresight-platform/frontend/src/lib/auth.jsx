import { createContext, useContext, useState } from "react";
import { api, setToken } from "./api.js";

const AuthCtx = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null); // { role, display_name, home, username }

  async function signIn(username, password) {
    const res = await api.login(username, password);
    setToken(res.token);
    const u = {
      role: res.role,
      display_name: res.display_name,
      home: res.home,
      username,
    };
    setUser(u);
    return u;
  }

  function signOut() {
    setToken(null);
    setUser(null);
  }

  return (
    <AuthCtx.Provider value={{ user, signIn, signOut }}>
      {children}
    </AuthCtx.Provider>
  );
}

export function useAuth() {
  return useContext(AuthCtx);
}
