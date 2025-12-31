import React from 'react'
import { FaTrophy } from 'react-icons/fa'
import { getTeamColor } from '../teamColors'

const PredictionResult = ({ prediction }) => {
  const { winner, confidence, home_team, away_team } = prediction
  
  const homeConfidence = winner === home_team ? confidence : 100 - confidence
  const awayConfidence = winner === away_team ? confidence : 100 - confidence
  
  const homeColor = getTeamColor(home_team)
  const awayColor = getTeamColor(away_team)
  const winnerColor = getTeamColor(winner)
  
  const spreadEquivalent = ((confidence - 50) * 0.2).toFixed(1)
  
  const getConfidenceLevel = (conf) => {
    if (conf >= 70) return 'Very High'
    if (conf >= 65) return 'High'
    if (conf >= 60) return 'Medium'
    if (conf >= 55) return 'Moderate'
    return 'Low'
  }

  return (
    <div className="card border-2" style={{ borderColor: winnerColor }}>
      <h2 className="card-header flex items-center gap-2 text-xl">
        <FaTrophy className="text-white" />
        Prediction Result
      </h2>
      
      <div className="text-center space-y-6">
        {/* Winner Display */}
        <div className="py-6">
          <div className="text-neutral-500 text-sm uppercase tracking-wide mb-2">Projected Winner</div>
          <div className="text-5xl font-bold" style={{ color: winnerColor }}>
            {winner.toUpperCase()}
          </div>
          <div className="text-xl text-neutral-300 mt-2">
            Win Probability: <span className="font-bold text-white">{confidence}%</span>
          </div>
        </div>

        {/* Progress Bars */}
        <div className="space-y-4">
          <div>
            <div className="flex justify-between mb-2 text-sm">
              <span className="font-semibold" style={{ color: homeColor }}>{home_team}</span>
              <span className="font-semibold" style={{ color: homeColor }}>{homeConfidence.toFixed(1)}%</span>
            </div>
            <div className="w-full bg-neutral-800 rounded-full h-3 overflow-hidden">
              <div
                className="progress-bar"
                style={{ width: `${homeConfidence}%`, backgroundColor: homeColor }}
              ></div>
            </div>
          </div>
          
          <div>
            <div className="flex justify-between mb-2 text-sm">
              <span className="font-semibold" style={{ color: awayColor }}>{away_team}</span>
              <span className="font-semibold" style={{ color: awayColor }}>{awayConfidence.toFixed(1)}%</span>
            </div>
            <div className="w-full bg-neutral-800 rounded-full h-3 overflow-hidden">
              <div
                className="progress-bar"
                style={{ width: `${awayConfidence}%`, backgroundColor: awayColor }}
              ></div>
            </div>
          </div>
        </div>

        {/* Additional Info */}
        <div className="grid md:grid-cols-2 gap-4 pt-6 border-t border-neutral-800">
          <div className="stat-card text-center">
            <div className="text-neutral-500 text-sm">Spread Equivalent</div>
            <div className="text-2xl font-bold mt-1 text-white">
              {winner} {spreadEquivalent > 0 ? '-' : '+'}{Math.abs(spreadEquivalent)}
            </div>
          </div>
          
          <div className="stat-card text-center">
            <div className="text-neutral-500 text-sm">Confidence Level</div>
            <div className="text-2xl font-bold mt-1 text-white">
              {getConfidenceLevel(confidence)}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default PredictionResult