"use client";

import { useState, useEffect } from "react";
import { getEvalResults, getAuditLog, getEscalations, getConversations } from "@/lib/api";

interface Props {
  token:    string;
  onLogout: () => void;
}

export default function AdminDashboard({ token, onLogout }: Props) {
  const [evalData,  setEvalData]  = useState<any>(null);
  const [auditLog,  setAuditLog]  = useState<any[]>([]);
  const [tab,       setTab]       = useState<"overview"|"audit"|"conversations">("overview");
  const [loading,   setLoading]   = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [ev, audit] = await Promise.all([
          getEvalResults(token),
          getAuditLog(token),
        ]);
        setEvalData(ev);
        setAuditLog(audit.logs || []);
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
          <div className="w-8 h-8 bg-purple-500 rounded-lg flex items-center justify-center">
            <span className="text-white text-sm font-bold">PW</span>
          </div>
          <div>
            <p className="text-white font-semibold">Admin Dashboard</p>
            <p className="text-purple-400 text-xs">admin</p>
          </div>
        </div>
        <button onClick={onLogout} className="text-gray-400 hover:text-white text-sm">
          Sign out
        </button>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-800 px-6">
        <div className="flex gap-6">
          {(["overview", "audit", "conversations"] as const).map(t => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`py-3 text-sm font-medium border-b-2 transition capitalize ${
                tab === t
                  ? "border-purple-500 text-purple-400"
                  : "border-transparent text-gray-400 hover:text-white"
              }`}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      <div className="p-6">
        {loading ? (
          <p className="text-gray-400">Loading...</p>
        ) : tab === "overview" ? (
          <div className="space-y-6">
            {/* Eval stats */}
            {evalData && (
              <>
                <h2 className="text-white font-semibold">Evaluation Results</h2>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {[
                    { label: "Pass Rate",  value: `${(evalData.pass_rate * 100).toFixed(1)}%`, color: "text-emerald-400" },
                    { label: "Passed",     value: evalData.passed,  color: "text-emerald-400" },
                    { label: "Failed",     value: evalData.failed,  color: "text-red-400" },
                    { label: "Total",      value: evalData.total,   color: "text-white" },
                  ].map(stat => (
                    <div key={stat.label} className="bg-gray-900 rounded-xl p-4 border border-gray-800">
                      <p className="text-gray-400 text-xs mb-1">{stat.label}</p>
                      <p className={`text-2xl font-bold ${stat.color}`}>{stat.value}</p>
                    </div>
                  ))}
                </div>

                {/* Category breakdown */}
                <h3 className="text-white font-medium">Category Breakdown</h3>
                <div className="space-y-2">
                  {Object.entries(evalData.categories || {}).map(([cat, stats]: [string, any]) => {
                    const rate = stats.passed / stats.total;
                    return (
                      <div key={cat} className="bg-gray-900 rounded-lg p-3 border border-gray-800">
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-gray-300 text-sm capitalize">{cat.replace(/_/g, " ")}</span>
                          <span className={`text-sm font-medium ${rate === 1 ? "text-emerald-400" : rate >= 0.5 ? "text-yellow-400" : "text-red-400"}`}>
                            {stats.passed}/{stats.total}
                          </span>
                        </div>
                        <div className="w-full bg-gray-800 rounded-full h-1.5">
                          <div
                            className={`h-1.5 rounded-full ${rate === 1 ? "bg-emerald-500" : rate >= 0.5 ? "bg-yellow-500" : "bg-red-500"}`}
                            style={{ width: `${rate * 100}%` }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </>
            )}
          </div>
        ) : tab === "audit" ? (
          <div className="space-y-3">
            <p className="text-gray-400 text-sm">{auditLog.length} recent audit events</p>
            {auditLog.map((log, i) => (
              <div key={i} className="bg-gray-900 rounded-xl p-4 border border-gray-800">
                <div className="flex items-center justify-between mb-1">
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                    log.event_type === "tool_call"       ? "bg-blue-900 text-blue-300" :
                    log.event_type === "tool_blocked"    ? "bg-red-900 text-red-300" :
                    log.event_type === "pii_detected"    ? "bg-yellow-900 text-yellow-300" :
                    log.event_type === "session_issued"  ? "bg-emerald-900 text-emerald-300" :
                    "bg-gray-800 text-gray-300"
                  }`}>
                    {log.event_type}
                  </span>
                  <span className="text-gray-500 text-xs">
                    {new Date(log.created_at).toLocaleString()}
                  </span>
                </div>
                <p className="text-gray-300 text-sm">Customer: {log.customer_id}</p>
                {log.tool_name && (
                  <p className="text-gray-400 text-xs mt-1">Tool: {log.tool_name} → {log.server_name}</p>
                )}
              </div>
            ))}
          </div>
        ) : (
          <div className="bg-gray-900 rounded-xl p-8 text-center border border-gray-800">
            <p className="text-gray-400">Conversation history visible to agents and admins via the API.</p>
            <p className="text-gray-500 text-sm mt-2">Use the Agent Dashboard to view conversations.</p>
          </div>
        )}
      </div>
    </div>
  );
}
