"use client";

import { useState } from "react";
import { login } from "@/lib/api";
import ChatPage from "@/components/ChatPage";
import AgentDashboard from "@/components/AgentDashboard";
import AdminDashboard from "@/components/AdminDashboard";

export default function Home() {
  const [token, setToken]       = useState("");
  const [role, setRole]         = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError]       = useState("");
  const [loading, setLoading]   = useState(false);

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const data = await login(username, password);
      setToken(data.access_token);
      setRole(data.role);
    } catch {
      setError("Invalid username or password");
    } finally {
      setLoading(false);
    }
  }

  function handleLogout() {
    setToken("");
    setRole("");
    setUsername("");
    setPassword("");
  }

  if (token) {
    if (role === "customer") return <ChatPage token={token} onLogout={handleLogout} />;
    if (role === "agent")    return <AgentDashboard token={token} role={role} onLogout={handleLogout} />;
    if (role === "admin")    return <AdminDashboard token={token} onLogout={handleLogout} />;
  }

  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center p-4">
      <div className="w-full max-w-md">

        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-emerald-500 rounded-2xl mb-4">
            <span className="text-2xl font-bold text-white">PW</span>
          </div>
          <h1 className="text-2xl font-bold text-white">PocketWallet</h1>
          <p className="text-gray-400 mt-1">AI Support Platform</p>
        </div>

        {/* Login form */}
        <div className="bg-gray-900 rounded-2xl p-8 border border-gray-800">
          <h2 className="text-lg font-semibold text-white mb-6">Sign in</h2>

          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label className="block text-sm text-gray-400 mb-1">Username</label>
              <input
                type="text"
                value={username}
                onChange={e => setUsername(e.target.value)}
                placeholder="ayesha / agent01 / admin01"
                className="w-full bg-gray-800 text-white rounded-lg px-4 py-3 border border-gray-700 focus:border-emerald-500 focus:outline-none"
                required
              />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">Password</label>
              <input
                type="password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder="customer123 / agent123 / admin123"
                className="w-full bg-gray-800 text-white rounded-lg px-4 py-3 border border-gray-700 focus:border-emerald-500 focus:outline-none"
                required
              />
            </div>

            {error && (
              <p className="text-red-400 text-sm">{error}</p>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-emerald-500 hover:bg-emerald-600 text-white font-semibold rounded-lg py-3 transition disabled:opacity-50"
            >
              {loading ? "Signing in..." : "Sign in"}
            </button>
          </form>

          {/* Demo credentials */}
          <div className="mt-6 p-4 bg-gray-800 rounded-lg">
            <p className="text-xs text-gray-400 font-semibold mb-2">DEMO CREDENTIALS</p>
            <div className="space-y-1 text-xs text-gray-300">
              <p><span className="text-emerald-400">Customer:</span> ayesha / customer123</p>
              <p><span className="text-blue-400">Agent:</span> agent01 / agent123</p>
              <p><span className="text-purple-400">Admin:</span> admin01 / admin123</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
