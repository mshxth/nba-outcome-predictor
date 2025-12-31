import { useState, useEffect } from 'react'
import axios from 'axios'
import { GiBasketballBall } from 'react-icons/gi'
import { BiStats } from 'react-icons/bi'
import { AiOutlineInfoCircle } from 'react-icons/ai'
import TeamSelector from './components/TeamSelector'
import PredictionResult from './components/PredictionResult'
import StatsComparison from './components/StatsComparison'
import ModelStats from './components/ModelStats'
import PredictionBreakdown from './components/PredictionBreakdown'

const API_BASE = 'http://localhost:8000'

function App() {
  const [activeTab, setActiveTab] = useState('predict')
  const [teams, setTeams] = useState([])
  const [homeTeam, setHomeTeam] = useState('')
  const [awayTeam, setAwayTeam] = useState('')
  const [prediction, setPrediction] = useState(null)
  const [teamComparison, setTeamComparison] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [modelStats, setModelStats] = useState(null)

  useEffect(() => {
    fetchTeams()
    fetchModelStats()
  }, [])

  const fetchTeams = async () => {
    try {
      const response = await axios.get(`${API_BASE}/api/teams`)
      setTeams(response.data.teams)
    } catch (err) {
      console.error('Failed to fetch teams:', err)
    }
  }

  const fetchModelStats = async () => {
    try {
      const response = await axios.get(`${API_BASE}/api/stats`)
      setModelStats(response.data)
    } catch (err) {
      console.error('Failed to fetch model stats:', err)
    }
  }

  const handlePredict = async () => {
    if (!homeTeam || !awayTeam) {
      setError('Please select both teams')
      return
    }

    if (homeTeam === awayTeam) {
      setError('Please select different teams')
      return
    }

    setLoading(true)
    setError(null)

    try {
      const [predictionResponse, comparisonResponse] = await Promise.all([
        axios.get(`${API_BASE}/api/predict`, {
          params: { home: homeTeam, away: awayTeam }
        }),
        axios.get(`${API_BASE}/api/team-comparison`, {
          params: { home: homeTeam, away: awayTeam }
        })
      ])
      
      setPrediction(predictionResponse.data)
      setTeamComparison(comparisonResponse.data)
    } catch (err) {
      setError(err.response?.data?.error || 'Prediction failed')
    } finally {
      setLoading(false)
    }
  }

  const tabs = [
    { id: 'predict', label: 'Predict', icon: <GiBasketballBall /> },
    { id: 'stats', label: 'Statistics', icon: <BiStats /> },
    { id: 'info', label: 'Info', icon: <AiOutlineInfoCircle /> }
  ]

  return (
    <div className="min-h-screen p-4 md:p-8 bg-black">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <header className="text-center mb-8">
          <div className="flex items-center justify-center gap-3 mb-2">
            <GiBasketballBall className="text-5xl text-white" />
            <h1 className="text-4xl md:text-5xl font-bold text-white">
              NBA Outcome Predictor
            </h1>
          </div>
          <p className="text-neutral-400 text-lg">
            Powered by Machine Learning
            {modelStats && (
              <span className="ml-3 text-white font-medium">
                Model Accuracy: {modelStats.accuracy}%
              </span>
            )}
          </p>
        </header>

        {/* Tabs */}
        <div className="flex justify-center gap-2 mb-8 border-b border-neutral-800">
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-6 py-3 font-semibold transition border-b-2 ${
                activeTab === tab.id
                  ? 'border-white text-white'
                  : 'border-transparent text-neutral-500 hover:text-neutral-300'
              }`}
            >
              {tab.icon}
              <span>{tab.label}</span>
            </button>
          ))}
        </div>

        {/* Tab Content */}
        {activeTab === 'predict' && (
          <div className="space-y-6">
            {/* Game Setup */}
            <div className="card">
              <h2 className="card-header">Game Setup</h2>
              
              <div className="grid md:grid-cols-2 gap-6">
                <TeamSelector
                  label="Home Team"
                  teams={teams}
                  selectedTeam={homeTeam}
                  onTeamChange={setHomeTeam}
                  placeholder="Select Home Team"
                />
                <TeamSelector
                  label="Away Team"
                  teams={teams}
                  selectedTeam={awayTeam}
                  onTeamChange={setAwayTeam}
                  placeholder="Select Away Team"
                />
              </div>

              <div className="mt-6 text-center">
                <button
                  onClick={handlePredict}
                  disabled={loading || !homeTeam || !awayTeam}
                  className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {loading ? 'Analyzing...' : 'Generate Prediction'}
                </button>
              </div>

              {error && (
                <div className="mt-4 p-4 bg-red-950 border border-red-900 rounded-lg text-red-200 text-center">
                  {error}
                </div>
              )}
            </div>

            {/* Stats Comparison */}
            {teamComparison && (
              <StatsComparison teamComparison={teamComparison} />
            )}

            {/* Prediction Result */}
            {prediction && (
              <PredictionResult prediction={prediction} />
            )}

            {/* Prediction Breakdown */}
            {prediction && teamComparison && (
              <PredictionBreakdown
                prediction={prediction}
                teamComparison={teamComparison}
              />
            )}

            {/* Model Stats Cards */}
            {modelStats && (
              <div className="grid md:grid-cols-3 gap-4">
                <div className="stat-card text-center">
                  <div className="text-3xl font-bold text-white">{modelStats.accuracy}%</div>
                  <div className="text-neutral-400 mt-1">Model Accuracy</div>
                </div>
                <div className="stat-card text-center">
                  <div className="text-3xl font-bold text-white">2,462</div>
                  <div className="text-neutral-400 mt-1">Total Games</div>
                </div>
                <div className="stat-card text-center">
                  <div className="text-3xl font-bold text-white">{modelStats.features}</div>
                  <div className="text-neutral-400 mt-1">Features Used</div>
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === 'stats' && modelStats && (
          <ModelStats modelStats={modelStats} />
        )}

        {activeTab === 'info' && (
          <div className="card">
            <h2 className="card-header">About This Project</h2>
            <div className="space-y-4 text-neutral-300">
              <p>
                This NBA game outcome predictor uses a <strong className="text-white">Random Forest machine learning model</strong> trained 
                on {modelStats?.features || 12} key basketball statistics to predict game winners.
              </p>
              <div>
                <h3 className="text-lg font-bold text-white mb-2">Features Used:</h3>
                <ul className="list-disc list-inside space-y-1">
                  <li>Offensive Rating (ORtg)</li>
                  <li>Effective Field Goal Percentage (eFG%)</li>
                  <li>Turnover Percentage (TOV%)</li>
                  <li>Offensive Rebound Percentage (ORB%)</li>
                  <li>Injury Impact (Value & Advanced Metrics)</li>
                  <li>Team Performance Trends</li>
                </ul>
              </div>
              <div>
                <h3 className="text-lg font-bold text-white mb-2">Model Performance:</h3>
                <p>
                  Achieves <strong className="text-white">{modelStats?.accuracy}% accuracy</strong> on test data,
                  competitive with professional sports analytics models.
                </p>
              </div>
              <div className="pt-4 border-t border-neutral-800">
                <p className="text-sm text-neutral-500">
                  Data sourced from Basketball Reference • Model: {modelStats?.model_type}
                </p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default App