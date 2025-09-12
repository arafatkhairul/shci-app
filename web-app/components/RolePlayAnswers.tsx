"use client";
import { useState, useEffect } from "react";
import { Database, Search, RefreshCw, MessageSquare } from "lucide-react";

interface RolePlayAnswer {
    question: string;
    answer: string;
    organization_name: string;
    role_title: string;
    template: string;
    created_at: string;
    updated_at: string;
}

interface RolePlayAnswersProps {
    clientId: string;
    isVisible: boolean;
    onClose: () => void;
}

export default function RolePlayAnswers({ clientId, isVisible, onClose }: RolePlayAnswersProps) {
    const [answers, setAnswers] = useState<RolePlayAnswer[]>([]);
    const [loading, setLoading] = useState(false);
    const [searchQuery, setSearchQuery] = useState("");
    const [stats, setStats] = useState<any>(null);
    const [error, setError] = useState<string | null>(null);

    const fetchAnswers = async () => {
        if (!clientId) return;
        
        setLoading(true);
        setError(null);
        
        try {
            const response = await fetch(`/roleplay/answers/${clientId}`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            setAnswers(data.answers || []);
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to fetch answers");
        } finally {
            setLoading(false);
        }
    };

    const fetchStats = async () => {
        try {
            const response = await fetch("/roleplay/stats");
            if (response.ok) {
                const data = await response.json();
                setStats(data.database_stats);
            }
        } catch (err) {
            console.error("Failed to fetch stats:", err);
        }
    };

    const searchAnswers = async () => {
        if (!searchQuery.trim() || !clientId) return;
        
        setLoading(true);
        setError(null);
        
        try {
            const response = await fetch(`/roleplay/search/${clientId}?question=${encodeURIComponent(searchQuery)}`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            if (data.found) {
                // Found exact match
                setAnswers([data.answer]);
            } else if (data.similar_answers) {
                // Found similar answers
                setAnswers(data.similar_answers);
            } else {
                setAnswers([]);
            }
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to search answers");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (isVisible && clientId) {
            fetchAnswers();
            fetchStats();
        }
    }, [isVisible, clientId]);

    if (!isVisible) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm">
            <div className="bg-gradient-to-br from-white/[0.05] to-white/[0.02] backdrop-blur-xl rounded-3xl border border-white/20 p-6 max-w-4xl w-full mx-4 max-h-[90vh] overflow-y-auto">
                <div className="flex items-center justify-between mb-6">
                    <div className="flex items-center gap-3">
                        <Database className="h-6 w-6 text-blue-400" />
                        <h2 className="text-2xl font-bold text-zinc-100">Role Play Database</h2>
                    </div>
                    <button
                        onClick={onClose}
                        className="text-zinc-400 hover:text-zinc-200 text-2xl"
                    >
                        ×
                    </button>
                </div>

                {/* Stats */}
                {stats && (
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                        <div className="bg-blue-500/10 p-4 rounded-xl border border-blue-400/30">
                            <div className="text-2xl font-bold text-blue-300">{stats.total_configs || 0}</div>
                            <div className="text-sm text-blue-400">Total Configs</div>
                        </div>
                        <div className="bg-green-500/10 p-4 rounded-xl border border-green-400/30">
                            <div className="text-2xl font-bold text-green-300">{stats.enabled_configs || 0}</div>
                            <div className="text-sm text-green-400">Active Configs</div>
                        </div>
                        <div className="bg-purple-500/10 p-4 rounded-xl border border-purple-400/30">
                            <div className="text-2xl font-bold text-purple-300">{stats.total_answers || 0}</div>
                            <div className="text-sm text-purple-400">Stored Answers</div>
                        </div>
                        <div className="bg-orange-500/10 p-4 rounded-xl border border-orange-400/30">
                            <div className="text-2xl font-bold text-orange-300">{stats.unique_organizations || 0}</div>
                            <div className="text-sm text-orange-400">Organizations</div>
                        </div>
                    </div>
                )}

                {/* Search */}
                <div className="flex gap-3 mb-6">
                    <div className="flex-1 relative">
                        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-zinc-400" />
                        <input
                            type="text"
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            placeholder="Search questions..."
                            className="w-full pl-10 pr-4 py-3 bg-white/[0.05] border border-white/10 rounded-xl text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-blue-400/50"
                            onKeyPress={(e) => e.key === "Enter" && searchAnswers()}
                        />
                    </div>
                    <button
                        onClick={searchAnswers}
                        disabled={loading || !searchQuery.trim()}
                        className="px-4 py-3 bg-blue-500/25 text-blue-200 border border-blue-400/30 rounded-xl hover:bg-blue-500/35 transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        Search
                    </button>
                    <button
                        onClick={fetchAnswers}
                        disabled={loading}
                        className="px-4 py-3 bg-green-500/25 text-green-200 border border-green-400/30 rounded-xl hover:bg-green-500/35 transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
                    </button>
                </div>

                {/* Error */}
                {error && (
                    <div className="bg-red-500/15 border border-red-400/40 rounded-xl p-4 mb-6">
                        <div className="flex items-center gap-3">
                            <div className="w-3 h-3 bg-red-400 rounded-full" />
                            <span className="text-red-200 font-semibold">Error: {error}</span>
                        </div>
                    </div>
                )}

                {/* Answers List */}
                <div className="space-y-4">
                    {loading ? (
                        <div className="flex items-center justify-center py-8">
                            <RefreshCw className="h-8 w-8 animate-spin text-blue-400" />
                            <span className="ml-3 text-zinc-300">Loading...</span>
                        </div>
                    ) : answers.length > 0 ? (
                        answers.map((answer, index) => (
                            <div key={index} className="bg-white/[0.05] rounded-xl p-6 border border-white/10 hover:bg-white/[0.08] transition-all duration-300">
                                <div className="flex items-start justify-between mb-4">
                                    <div className="flex items-center gap-3">
                                        <MessageSquare className="h-5 w-5 text-blue-400" />
                                        <div>
                                            <h3 className="font-semibold text-zinc-200">Question</h3>
                                            <p className="text-sm text-zinc-400">{answer.organization_name} • {answer.role_title}</p>
                                        </div>
                                    </div>
                                    <div className="text-xs text-zinc-500">
                                        {new Date(answer.created_at).toLocaleDateString()}
                                    </div>
                                </div>
                                
                                <div className="space-y-3">
                                    <div>
                                        <h4 className="text-sm font-semibold text-zinc-300 mb-2">Question:</h4>
                                        <p className="text-zinc-200 bg-white/[0.03] p-3 rounded-lg border border-white/10">
                                            {answer.question}
                                        </p>
                                    </div>
                                    
                                    <div>
                                        <h4 className="text-sm font-semibold text-zinc-300 mb-2">Answer:</h4>
                                        <p className="text-zinc-200 bg-white/[0.03] p-3 rounded-lg border border-white/10">
                                            {answer.answer}
                                        </p>
                                    </div>
                                </div>
                                
                                <div className="mt-4 flex items-center gap-4 text-xs text-zinc-500">
                                    <span>Template: {answer.template}</span>
                                    <span>Updated: {new Date(answer.updated_at).toLocaleString()}</span>
                                </div>
                            </div>
                        ))
                    ) : (
                        <div className="text-center py-8">
                            <Database className="h-16 w-16 mx-auto mb-4 opacity-30 text-zinc-500" />
                            <p className="text-zinc-400 font-semibold mb-2">
                                {searchQuery ? "No answers found" : "No stored answers yet"}
                            </p>
                            <p className="text-zinc-600 text-sm">
                                {searchQuery 
                                    ? "Try a different search term" 
                                    : "Start role play conversations to build the database"
                                }
                            </p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}


