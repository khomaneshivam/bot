import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import { api } from "../services/api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [isGuest, setIsGuest] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [authError, setAuthError] = useState(null);
  const [isLoginModalOpen, setIsLoginModalOpen] = useState(false);
  const [isProfileModalOpen, setIsProfileModalOpen] = useState(false);

  const fetchCurrentUser = useCallback(async () => {
    const token = typeof localStorage !== "undefined" ? localStorage.getItem("quant_auth_token") : null;
    if (!token) {
      setUser(null);
      setIsGuest(false);
      setIsLoading(false);
      return;
    }

    try {
      const res = await api.getMe();
      if (res && res.id) {
        setUser(res);
        setIsGuest(false);
        setAuthError(null);
      } else {
        localStorage.removeItem("quant_auth_token");
        setUser(null);
      }
    } catch (err) {
      console.warn("[AuthContext] Session expired or invalid:", err);
      localStorage.removeItem("quant_auth_token");
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchCurrentUser();
  }, [fetchCurrentUser]);

  const login = async (username, password) => {
    setAuthError(null);
    try {
      const res = await api.login(username, password);
      if (res.access_token) {
        localStorage.setItem("quant_auth_token", res.access_token);
        setUser({
          id: res.user_id,
          username: res.username,
          role: res.role,
        });
        setIsGuest(false);
        setIsLoginModalOpen(false);
        return { success: true };
      }
      throw new Error(res.detail || "Authentication failed");
    } catch (err) {
      const msg = err.message || "Invalid credentials";
      setAuthError(msg);
      return { success: false, error: msg };
    }
  };

  const register = async ({ username, password, confirmPassword, role, adminKey }) => {
    setAuthError(null);
    try {
      const res = await api.register({ username, password, confirmPassword, role, adminKey });
      if (res.access_token) {
        localStorage.setItem("quant_auth_token", res.access_token);
        setUser({
          id: res.user_id,
          username: res.username,
          role: res.role,
        });
        setIsGuest(false);
        setIsLoginModalOpen(false);
        return { success: true };
      }
      throw new Error(res.detail || "Registration failed");
    } catch (err) {
      const msg = err.message || "Registration failed";
      setAuthError(msg);
      return { success: false, error: msg };
    }
  };

  const logout = async () => {
    try {
      await api.logout();
    } catch (err) {
      console.warn("[Auth] Logout error:", err);
    } finally {
      localStorage.removeItem("quant_auth_token");
      setUser(null);
      setIsGuest(false);
    }
  };

  const enterAsGuest = () => {
    setIsGuest(true);
    setUser({
      id: "usr_guest",
      username: "Observer",
      role: "READ_ONLY",
    });
    setAuthError(null);
  };

  const hasRole = (requiredRole) => {
    if (!user) return false;
    const userRole = (user.role || "").toUpperCase();
    const req = (requiredRole || "").toUpperCase();

    if (userRole === "ADMIN") return true;
    if ((req === "TRADER" || req === "READ_ONLY" || req === "VIEWER") && userRole === "TRADER") return true;
    if (req === "READ_ONLY" || req === "VIEWER") return true;
    return userRole === req;
  };

  const changePassword = async ({ oldPassword, newPassword, confirmPassword }) => {
    try {
      const res = await api.changePassword({ oldPassword, newPassword, confirmPassword });
      return { success: true, message: res.message || "Passphrase updated successfully." };
    } catch (err) {
      return { success: false, error: err.message || "Failed to update passphrase." };
    }
  };

  const value = {
    user,
    isAuthenticated: Boolean(user && !isGuest),
    isGuest,
    isLoading,
    authError,
    setAuthError,
    isLoginModalOpen,
    setIsLoginModalOpen,
    isProfileModalOpen,
    setIsProfileModalOpen,
    login,
    register,
    logout,
    changePassword,
    enterAsGuest,
    hasRole,
    refreshUser: fetchCurrentUser,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
