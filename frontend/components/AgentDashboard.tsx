"use client";

import { useState, useEffect } from "react";
import { getEscalations, getConversations } from "@/lib/api";

interface Props {
  token:    string;
  role:     string;
  onLogout: () => void;
}

export default function AgentDashboard({ token, role, onLogout }: Props) {
  const [escalations,   setEscalations]   = useState<any[]>([]);
  const [conversations, setConversations] = useState<any[]>([]);
  const [tab,           setTab]           = useState<"escalations"|"conversations">("escalations");
  const [loading,       setLoading]       = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [esc, conv] = await Promise.all([
          getEscalations(token),
          getConversations(token),
        ]);
        setEscalations(esc.escalations || []);
        setConversations(Array.isArray(conv) ? conv : []);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [token]);

  return (
    <div className="min-h-screen bg-gray-950">

      {/* Header */}
      <div className="bg-gray-900 border-b border-gray-800 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-blue-500 rounded-lg flex items-center justify-center">
            <span className="text-white text-sm font-bold">PW</span>
          </div>
          <div>
            <p className="text-white font-semibold">Agent Dashboard</p>
            <p className="text-blue-400 text-xs capitalize">{role}</p>
          </div>
        </div>
        <button onClick={onLogout} className="text-gray-400 hover:text-white text-sm">
          Sign out
        </button>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-800 px-6">
        <div className="flex gap-6">
          {(["escalations", "conversations"] as const).map(t => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`py-3 text-sm font-medium border-b-2 transition capitalize ${
                tab === t
                  ? "border-blue-500 text-blue-400"
                  : "border-transparent text-gray-400 hover:text-white"
              }`}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="p-6">
        {loading ? (
          <p className="text-gray-400">Loading...</p>
        ) : tab === "escalations" ? (
          <div className="space-y-3">
            <p className="text-gray-400 text-sm">{escalations.length} escalations</p>
            {escalations.length === 0 ? (
              <div className="bg-gray-900 rounded-xl p-8 text-center">
                <p className="text-gray-400">No escalations at this time</p>
              </div>
            ) : (
              escalations.map((e, i) => (
                <div key={i} className="bg-gray-900 rounded-xl p-4 border border-gray-800">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-white font-medium text-sm">{e.id}</span>
                    <span className={`text-xs px-2 py-1 rounded-full ${
                      e.passed === false
                        ? "bg-red-900 text-red-300"
                        : "bg-gray-800 text-gray-300"
                    }`}>
                      {e.passed === false ? "Failed" : "Review"}
                    </span>
                  </div>
                  <p className="text-gray-400 text-xs">{e.category}</p>
                  <p className="text-gray-300 text-sm mt-1 line-clamp-2">{e.message}</p>
                </div>
              ))
            )}
          </div>
        ) : (
          <div className="space-y-3">
            <p className="text-gray-400 text-sm">{conversations.length} conversations</p>
            {conversations.length === 0 ? (
              <div className="bg-gray-900 rounded-xl p-8 text-center">
                <p className="text-gray-400">No conversations yet</p>
              </div>
            ) : (
              conversations.map((c, i) => (
                <div key={i} className="bg-gray-900 rounded-xl p-4 border border-gray-800">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-white font-medium text-sm">{c.username}</span>
                    <span className="text-gray-500 text-xs">
                      {new Date(c.updated_at).toLocaleString()}
                    </span>
                  </div>
                  <p className="text-gray-400 text-xs">{c.conversation_id}</p>
                  <p className="text-gray-300 text-sm mt-1">
                    {c.messages?.length || 0} messages
                  </p>
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  );
}
