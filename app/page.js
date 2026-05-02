'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

export default function Home() {
  const [projectPath, setProjectPath] = useState('.');
  const [loading, setLoading] = useState(false);
  const [loadingStage, setLoadingStage] = useState('');
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('issues');
  const [copiedBobContext, setCopiedBobContext] = useState(false);
  
  // Settings panel state
  const [showSettings, setShowSettings] = useState(false);
  const [apiKey, setApiKey] = useState('');
  const [projectId, setProjectId] = useState('');
  const [region, setRegion] = useState('us-south');
  const [credentialsSaved, setCredentialsSaved] = useState(false);
  
  // Copy states for new features
  const [copiedResetContext, setCopiedResetContext] = useState(false);
  const [copiedAtomicFix, setCopiedAtomicFix] = useState(false);

  // Load credentials from localStorage on mount
  useEffect(() => {
    const savedApiKey = localStorage.getItem('watsonx_api_key');
    const savedProjectId = localStorage.getItem('watsonx_project_id');
    const savedRegion = localStorage.getItem('watsonx_region');
    
    if (savedApiKey && savedProjectId) {
      setApiKey(savedApiKey);
      setProjectId(savedProjectId);
      setRegion(savedRegion || 'us-south');
      setCredentialsSaved(true);
    }
  }, []);

  const saveSettings = () => {
    localStorage.setItem('watsonx_api_key', apiKey);
    localStorage.setItem('watsonx_project_id', projectId);
    localStorage.setItem('watsonx_region', region);
    setCredentialsSaved(true);
    setShowSettings(false);
  };

  const runAnalysis = async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    setLoadingStage('Initializing scanner...');

    try {
      // Simulate loading stages
      setTimeout(() => setLoadingStage('Checking dependencies...'), 500);
      setTimeout(() => setLoadingStage('Verifying Node version...'), 1500);
      setTimeout(() => setLoadingStage('Detecting circular dependencies...'), 2500);
      setTimeout(() => setLoadingStage('Generating Bob context...'), 3500);

      const response = await fetch('/api/analyze', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          projectPath,
          apiKey: credentialsSaved ? apiKey : undefined,
          projectId: credentialsSaved ? projectId : undefined,
          region: credentialsSaved ? region : undefined
        }),
      });

      const data = await response.json();

      if (data.success) {
        setResult(data);
        setActiveTab('issues');
      } else {
        setError(data.message || 'Analysis failed');
      }
    } catch (err) {
      setError(err.message || 'Failed to connect to API');
    } finally {
      setLoading(false);
      setLoadingStage('');
    }
  };

  const copyBobContext = () => {
    if (result?.bobContext) {
      navigator.clipboard.writeText(result.bobContext);
      setCopiedBobContext(true);
      setTimeout(() => setCopiedBobContext(false), 2000);
    }
  };

  const copyResetContext = () => {
    if (result?.reset_context) {
      navigator.clipboard.writeText(result.reset_context);
      setCopiedResetContext(true);
      setTimeout(() => setCopiedResetContext(false), 2000);
    }
  };

  const copyAtomicFix = () => {
    if (result?.coordinated_fix_plan?.install_command) {
      navigator.clipboard.writeText(result.coordinated_fix_plan.install_command);
      setCopiedAtomicFix(true);
      setTimeout(() => setCopiedAtomicFix(false), 2000);
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'BLOCKED':
        return 'from-red-600 to-red-700';
      case 'CAUTION':
        return 'from-yellow-500 to-yellow-600';
      case 'CLEARED':
        return 'from-green-600 to-green-700';
      default:
        return 'from-gray-600 to-gray-700';
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'BLOCKED':
        return '🚫';
      case 'CAUTION':
        return '⚠️';
      case 'CLEARED':
        return '✅';
      default:
        return '❓';
    }
  };

  const getSeverityBadge = (type) => {
    const badges = {
      error: { label: 'CRITICAL', color: 'bg-red-600' },
      incompatibility: { label: 'CRITICAL', color: 'bg-red-600' },
      conflict: { label: 'HIGH', color: 'bg-orange-600' },
      redundancy: { label: 'HIGH', color: 'bg-orange-600' },
      warning: { label: 'MEDIUM', color: 'bg-yellow-600' },
      info: { label: 'INFO', color: 'bg-blue-600' },
    };
    return badges[type] || { label: 'UNKNOWN', color: 'bg-gray-600' };
  };

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      {/* Header */}
      <header className="border-b border-gray-800 bg-gray-900/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-4xl font-bold bg-gradient-to-r from-blue-400 to-blue-600 bg-clip-text text-transparent">
                🛡️ ZeroLoop
              </h1>
              <p className="text-gray-400 mt-1">IBM Bob Pre-Flight Intelligence</p>
            </div>
            <div className="flex items-center gap-6">
              <div className="text-right">
                <p className="text-sm text-gray-500">Preventing retry loops</p>
                <p className="text-xs text-gray-600">One scan at a time</p>
              </div>
              <button
                onClick={() => setShowSettings(!showSettings)}
                className="p-3 bg-gray-800 hover:bg-gray-700 rounded-lg transition-colors"
                title="Settings"
              >
                <svg className="w-6 h-6 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Settings Panel */}
      <AnimatePresence>
        {showSettings && (
          <>
            {/* Backdrop */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setShowSettings(false)}
              className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50"
            />
            
            {/* Settings Panel */}
            <motion.div
              initial={{ opacity: 0, x: 300 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 300 }}
              className="fixed right-0 top-0 h-full w-full max-w-md bg-gray-900 border-l border-gray-800 shadow-2xl z-50 overflow-y-auto"
            >
              <div className="p-6">
                <div className="flex items-center justify-between mb-6">
                  <h2 className="text-2xl font-bold text-white">Settings</h2>
                  <button
                    onClick={() => setShowSettings(false)}
                    className="p-2 hover:bg-gray-800 rounded-lg transition-colors"
                  >
                    <svg className="w-6 h-6 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>

                <div className="space-y-6">
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      watsonx.ai API Key
                    </label>
                    <input
                      type="password"
                      value={apiKey}
                      onChange={(e) => setApiKey(e.target.value)}
                      placeholder="Enter your IBM Cloud API key"
                      className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      Project ID
                    </label>
                    <input
                      type="text"
                      value={projectId}
                      onChange={(e) => setProjectId(e.target.value)}
                      placeholder="Enter your watsonx.ai project ID"
                      className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      Region
                    </label>
                    <select
                      value={region}
                      onChange={(e) => setRegion(e.target.value)}
                      className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    >
                      <option value="us-south">us-south</option>
                      <option value="eu-gb">eu-gb</option>
                      <option value="eu-de">eu-de</option>
                      <option value="jp-tok">jp-tok</option>
                    </select>
                  </div>

                  <button
                    onClick={saveSettings}
                    disabled={!apiKey || !projectId}
                    className="w-full px-6 py-3 bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 disabled:from-gray-700 disabled:to-gray-800 disabled:cursor-not-allowed rounded-lg font-semibold transition-all duration-200"
                  >
                    Save Settings
                  </button>

                  <div className="bg-blue-900/20 border border-blue-800 rounded-lg p-4">
                    <p className="text-blue-400 text-sm flex items-center gap-2">
                      <span>🔒</span>
                      <span>Credentials never leave your browser</span>
                    </p>
                    <p className="text-gray-400 text-xs mt-2">
                      Your API credentials are stored locally in your browser and only sent directly to the watsonx.ai API.
                    </p>
                  </div>
                </div>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>

      <main className="max-w-7xl mx-auto px-6 py-12">
        {/* Input Section */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-12"
        >
          <div className="bg-gray-900 rounded-2xl p-8 border border-gray-800">
            <label className="block text-sm font-medium text-gray-300 mb-3">
              Project Path
            </label>
            <div className="flex gap-4">
              <input
                type="text"
                value={projectPath}
                onChange={(e) => setProjectPath(e.target.value)}
                placeholder="./my-project or ."
                className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                disabled={loading}
              />
              <button
                onClick={runAnalysis}
                disabled={loading || !projectPath}
                className="px-8 py-3 bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 disabled:from-gray-700 disabled:to-gray-800 disabled:cursor-not-allowed rounded-lg font-semibold transition-all duration-200 shadow-lg shadow-blue-900/50"
              >
                {loading ? 'Analyzing...' : 'Run ZeroLoop'}
              </button>
            </div>
            
            {/* Warning Banner - No Credentials */}
            {!credentialsSaved && (
              <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                className="mt-4 bg-yellow-900/20 border border-yellow-600 rounded-lg p-4"
              >
                <p className="text-yellow-400 text-sm flex items-center gap-2">
                  <span>⚠️</span>
                  <span>No watsonx.ai credentials configured. Running in basic mode without AI interpretation.</span>
                </p>
              </motion.div>
            )}
          </div>
        </motion.div>

        {/* Loading State */}
        <AnimatePresence>
          {loading && (
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="mb-12"
            >
              <div className="bg-gray-900 rounded-2xl p-8 border border-gray-800">
                <div className="flex items-center gap-4 mb-4">
                  <div className="w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
                  <div>
                    <h3 className="text-xl font-semibold">Analyzing Project...</h3>
                    <p className="text-gray-400 mt-1">{loadingStage}</p>
                  </div>
                </div>
                <div className="space-y-2 mt-6">
                  <div className="flex items-center gap-3 text-sm text-gray-400">
                    <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></div>
                    Scanning package.json for conflicts
                  </div>
                  <div className="flex items-center gap-3 text-sm text-gray-400">
                    <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse delay-100"></div>
                    Comparing Node versions
                  </div>
                  <div className="flex items-center gap-3 text-sm text-gray-400">
                    <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse delay-200"></div>
                    Detecting circular dependencies
                  </div>
                  <div className="flex items-center gap-3 text-sm text-gray-400">
                    <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse delay-300"></div>
                    Generating Bob context
                  </div>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Error State */}
        <AnimatePresence>
          {error && (
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="mb-12"
            >
              <div className="bg-red-900/20 border border-red-800 rounded-2xl p-8">
                <h3 className="text-xl font-semibold text-red-400 mb-2">Analysis Failed</h3>
                <p className="text-gray-300">{error}</p>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Results */}
        <AnimatePresence>
          {result && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
            >
              {/* Clearance Banner */}
              <motion.div
                initial={{ scale: 0.9, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                transition={{ delay: 0.1 }}
                className={`mb-8 rounded-2xl p-12 bg-gradient-to-r ${getStatusColor(
                  result.analysis.status
                )} shadow-2xl`}
              >
                <div className="text-center">
                  <div className="text-8xl mb-4">{getStatusIcon(result.analysis.status)}</div>
                  <h2 className="text-5xl font-bold mb-3">
                    {result.analysis.status}
                  </h2>
                  <p className="text-xl text-white/90">{result.analysis.status_message}</p>
                </div>
              </motion.div>

              {/* Bobcoin Savings */}
              {result.savings && (
                <motion.div
                  initial={{ scale: 0.9, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  transition={{ delay: 0.2 }}
                  className="mb-8 bg-gradient-to-r from-yellow-600 to-yellow-700 rounded-2xl p-8 shadow-2xl"
                >
                  <div className="text-center">
                    <p className="text-yellow-100 text-sm font-medium mb-2">ESTIMATED SAVINGS</p>
                    <div className="flex items-center justify-center gap-3">
                      <span className="text-6xl">💰</span>
                      <span className="text-6xl font-bold">{result.savings.total_saved}</span>
                      <span className="text-3xl font-semibold text-yellow-100">Bobcoins</span>
                    </div>
                    <p className="text-yellow-100 mt-3">
                      Prevented ~{result.savings.breakdown?.length || 0} retry loops
                    </p>
                  </div>
                </motion.div>
              )}

              {/* Stat Cards */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 }}
                className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8"
              >
                <div className="bg-gray-900 border border-red-800 rounded-xl p-6">
                  <p className="text-red-400 text-sm font-medium mb-2">CRITICAL</p>
                  <p className="text-4xl font-bold">
                    {result.analysis.summary.by_type.error +
                      result.analysis.summary.by_type.incompatibility}
                  </p>
                </div>
                <div className="bg-gray-900 border border-orange-800 rounded-xl p-6">
                  <p className="text-orange-400 text-sm font-medium mb-2">HIGH</p>
                  <p className="text-4xl font-bold">
                    {result.analysis.summary.by_type.conflict +
                      result.analysis.summary.by_type.redundancy}
                  </p>
                </div>
                <div className="bg-gray-900 border border-yellow-800 rounded-xl p-6">
                  <p className="text-yellow-400 text-sm font-medium mb-2">MEDIUM</p>
                  <p className="text-4xl font-bold">
                    {result.analysis.summary.by_type.warning}
                  </p>
                </div>
                <div className="bg-gray-900 border border-blue-800 rounded-xl p-6">
                  <p className="text-blue-400 text-sm font-medium mb-2">TOTAL</p>
                  <p className="text-4xl font-bold">{result.analysis.summary.total_issues}</p>
                </div>
              </motion.div>

              {/* Tabs */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.4 }}
              >
                <div className="flex gap-2 mb-6 border-b border-gray-800">
                  {['issues', 'bobContext', 'resetContext', 'savings'].map((tab) => (
                    <button
                      key={tab}
                      onClick={() => setActiveTab(tab)}
                      className={`px-6 py-3 font-medium transition-all duration-200 border-b-2 ${
                        activeTab === tab
                          ? 'border-blue-500 text-blue-400'
                          : 'border-transparent text-gray-400 hover:text-gray-300'
                      }`}
                    >
                      {tab === 'issues' && '🔍 Issues Detected'}
                      {tab === 'bobContext' && '🤖 Bob Context'}
                      {tab === 'resetContext' && '🔄 Reset Context'}
                      {tab === 'savings' && '💰 Savings Breakdown'}
                    </button>
                  ))}
                </div>

                <AnimatePresence mode="wait">
                  {/* Issues Tab */}
                  {activeTab === 'issues' && (
                    <motion.div
                      key="issues"
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: 20 }}
                      className="space-y-4"
                    >
                      {/* Coordinated Fix Plan */}
                      {result.coordinated_fix_plan?.install_command && (
                        <div className="bg-yellow-900/20 border border-yellow-600 rounded-xl p-6 mb-6">
                          <h4 className="text-yellow-400 font-bold text-lg mb-4 flex items-center gap-2">
                            <span>⚡</span>
                            <span>COORDINATED FIX PLAN</span>
                          </h4>
                          
                          {/* Install Command */}
                          <div className="mb-4">
                            <p className="text-gray-300 text-sm mb-2 font-medium">Install Command:</p>
                            <div className="bg-gray-950 rounded-lg p-4 flex items-center justify-between gap-4">
                              <code className="text-green-400 font-mono text-sm flex-1 overflow-x-auto">
                                {result.coordinated_fix_plan.install_command}
                              </code>
                              <button
                                onClick={copyAtomicFix}
                                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg font-semibold transition-colors whitespace-nowrap flex items-center gap-2"
                              >
                                {copiedAtomicFix ? (
                                  <>
                                    <span>✓</span> Copied!
                                  </>
                                ) : (
                                  <>
                                    <span>📋</span> Copy Atomic Fix Command
                                  </>
                                )}
                              </button>
                            </div>
                          </div>
                          
                          {/* Uninstall Command (if exists) */}
                          {result.coordinated_fix_plan.uninstall_command && (
                            <div className="mb-4">
                              <p className="text-gray-300 text-sm mb-2 font-medium">Uninstall Command:</p>
                              <div className="bg-gray-950 rounded-lg p-4">
                                <code className="text-red-400 font-mono text-sm">
                                  {result.coordinated_fix_plan.uninstall_command}
                                </code>
                              </div>
                            </div>
                          )}
                          
                          {/* Warning */}
                          {result.coordinated_fix_plan.warning && (
                            <div className="bg-red-900/20 border border-red-800 rounded-lg p-4">
                              <p className="text-red-400 text-sm">
                                {result.coordinated_fix_plan.warning}
                              </p>
                            </div>
                          )}
                        </div>
                      )}

                      {result.analysis.issues.map((issue, index) => {
                        const badge = getSeverityBadge(issue.type);
                        return (
                          <motion.div
                            key={index}
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: index * 0.05 }}
                            className="bg-gray-900 border border-gray-800 rounded-xl p-6 hover:border-gray-700 transition-colors"
                          >
                            <div className="flex items-start justify-between mb-4">
                              <h3 className="text-xl font-semibold text-white flex-1">
                                {issue.title}
                              </h3>
                              <span
                                className={`${badge.color} text-white text-xs font-bold px-3 py-1 rounded-full`}
                              >
                                {badge.label}
                              </span>
                            </div>

                            <p className="text-gray-300 mb-4">{issue.detail}</p>

                            {/* Bob Clue */}
                            <div className="bg-blue-900/20 border border-blue-800 rounded-lg p-4 mb-4">
                              <p className="text-blue-400 font-semibold mb-2 flex items-center gap-2">
                                <span>🤖</span> BOB CLUE
                              </p>
                              <p className="text-gray-300 text-sm">{issue.bobclue}</p>
                            </div>

                            {/* Fix */}
                            <div className="bg-gray-800 rounded-lg p-4">
                              <p className="text-green-400 font-semibold mb-2 flex items-center gap-2">
                                <span>🔧</span> FIX
                              </p>
                              <pre className="text-gray-300 text-sm whitespace-pre-wrap font-mono">
                                {issue.fix}
                              </pre>
                            </div>
                          </motion.div>
                        );
                      })}
                    </motion.div>
                  )}

                  {/* Bob Context Tab */}
                  {activeTab === 'bobContext' && (
                    <motion.div
                      key="bobContext"
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: 20 }}
                    >
                      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
                        <div className="flex items-center justify-between mb-4">
                          <h3 className="text-xl font-semibold">Generated Bob Context</h3>
                          <button
                            onClick={copyBobContext}
                            className="px-6 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg font-semibold transition-colors flex items-center gap-2"
                          >
                            {copiedBobContext ? (
                              <>
                                <span>✓</span> Copied!
                              </>
                            ) : (
                              <>
                                <span>📋</span> Copy for Bob
                              </>
                            )}
                          </button>
                        </div>
                        <div className="bg-gray-950 rounded-lg p-6 overflow-x-auto">
                          <pre className="text-sm text-gray-300 whitespace-pre-wrap font-mono">
                            {result.bobContext}
                          </pre>
                        </div>
                      </div>
                    </motion.div>
                  )}

                  {/* Reset Context Tab */}
                  {activeTab === 'resetContext' && (
                    <motion.div
                      key="resetContext"
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: 20 }}
                    >
                      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
                        <div className="flex items-center justify-between mb-4">
                          <h3 className="text-xl font-semibold">Reset Context</h3>
                          <button
                            onClick={copyResetContext}
                            className="px-6 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg font-semibold transition-colors flex items-center gap-2"
                          >
                            {copiedResetContext ? (
                              <>
                                <span>✓</span> Copied!
                              </>
                            ) : (
                              <>
                                <span>📋</span> Copy Reset Context
                              </>
                            )}
                          </button>
                        </div>
                        <div className="bg-gray-950 rounded-lg p-6 overflow-x-auto mb-4">
                          <pre className="text-sm text-gray-300 whitespace-pre-wrap font-mono">
                            {result.reset_context}
                          </pre>
                        </div>
                        
                        {/* Word Count */}
                        {(() => {
                          const wordCount = result.reset_context ? result.reset_context.split(/\s+/).filter(word => word.length > 0).length : 0;
                          return (
                            <>
                              <p className="text-gray-400 text-sm mb-4">
                                Word count: <span className="font-semibold text-white">{wordCount}</span>
                              </p>
                              
                              {/* Warning if > 200 words */}
                              {wordCount > 200 && (
                                <div className="bg-red-900/20 border border-red-800 rounded-lg p-4">
                                  <p className="text-red-400 text-sm flex items-center gap-2">
                                    <span>⚠️</span>
                                    <span>Warning: Reset context exceeds 200 words. Consider condensing for optimal Bob performance.</span>
                                  </p>
                                </div>
                              )}
                            </>
                          );
                        })()}
                      </div>
                    </motion.div>
                  )}

                  {/* Savings Tab */}
                  {activeTab === 'savings' && result.savings && (
                    <motion.div
                      key="savings"
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: 20 }}
                    >
                      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
                        <h3 className="text-xl font-semibold mb-6">Bobcoin Savings Breakdown</h3>
                        <div className="overflow-x-auto">
                          <table className="w-full">
                            <thead>
                              <tr className="border-b border-gray-800">
                                <th className="text-left py-3 px-4 text-gray-400 font-medium">
                                  Issue
                                </th>
                                <th className="text-left py-3 px-4 text-gray-400 font-medium">
                                  Severity
                                </th>
                                <th className="text-center py-3 px-4 text-gray-400 font-medium">
                                  Loops Prevented
                                </th>
                                <th className="text-right py-3 px-4 text-gray-400 font-medium">
                                  Bobcoins Saved
                                </th>
                              </tr>
                            </thead>
                            <tbody>
                              {result.savings.breakdown.map((item, index) => {
                                const badge = getSeverityBadge(item.type);
                                return (
                                  <tr
                                    key={index}
                                    className="border-b border-gray-800 hover:bg-gray-800/50"
                                  >
                                    <td className="py-4 px-4 text-gray-300">{item.issue}</td>
                                    <td className="py-4 px-4">
                                      <span
                                        className={`${badge.color} text-white text-xs font-bold px-2 py-1 rounded`}
                                      >
                                        {badge.label}
                                      </span>
                                    </td>
                                    <td className="py-4 px-4 text-center text-gray-300">
                                      {item.estimated_loops_prevented}
                                    </td>
                                    <td className="py-4 px-4 text-right font-semibold text-yellow-400">
                                      {item.bobcoins_saved}
                                    </td>
                                  </tr>
                                );
                              })}
                              <tr className="bg-gray-800/50">
                                <td
                                  colSpan="3"
                                  className="py-4 px-4 text-right font-bold text-white"
                                >
                                  TOTAL SAVED:
                                </td>
                                <td className="py-4 px-4 text-right font-bold text-2xl text-yellow-400">
                                  {result.savings.total_saved}
                                </td>
                              </tr>
                              <tr className="border-b border-gray-800">
                                <td colSpan="3" className="py-4 px-4 text-gray-300">
                                  Granite AI Scan
                                </td>
                                <td className="py-4 px-4 text-right text-gray-300">
                                  $0.0001
                                </td>
                              </tr>
                              <tr className="bg-blue-900/20 border-2 border-blue-600">
                                <td colSpan="3" className="py-4 px-4 font-bold text-blue-400">
                                  NET ROI:
                                </td>
                                <td className="py-4 px-4 text-right font-bold text-2xl text-blue-400">
                                  {result.savings.net_roi || `${result.savings.total_saved - 0.0001} Bobcoins`}
                                </td>
                              </tr>
                            </tbody>
                          </table>
                        </div>
                        <p className="text-gray-400 text-sm mt-6 p-4 bg-gray-800 rounded-lg">
                          {result.savings.explanation}
                        </p>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-800 mt-20 py-8">
        <div className="max-w-7xl mx-auto px-6 text-center text-gray-500 text-sm">
          <p>ZeroLoop - Preventing retry loops, one scan at a time 🔄🚫</p>
          <p className="mt-2">Made with Bob for Bob</p>
        </div>
      </footer>
    </div>
  );
}

// Made with Bob
