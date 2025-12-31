import React from 'react'
import { getTeamColor } from '../teamColors'

const PredictionBreakdown = ({ prediction, teamComparison }) => {
  const { winner } = prediction
  const { home_team, away_team, breakdown } = teamComparison
  
  const homeColor = getTeamColor(home_team)
  const awayColor = getTeamColor(away_team)
  const winnerColor = getTeamColor(winner)
  
  const ortg_diff = Math.abs(breakdown.home.off_rtg - breakdown.away.off_rtg).toFixed(1)
  const efg_diff = Math.abs(breakdown.home.efg_pct - breakdown.away.efg_pct).toFixed(1)
  const tov_diff = Math.abs(breakdown.home.tov_pct - breakdown.away.tov_pct).toFixed(1)
  const orb_diff = Math.abs(breakdown.home.orb_pct - breakdown.away.orb_pct).toFixed(1)
  
  const factors = [
    { 
      label: 'Offensive Rating',
      leader: breakdown.home.off_rtg > breakdown.away.off_rtg ? home_team : away_team,
      leaderColor: breakdown.home.off_rtg > breakdown.away.off_rtg ? homeColor : awayColor,
      diff: `+${ortg_diff}`,
      favorsWinner: (breakdown.home.off_rtg > breakdown.away.off_rtg ? home_team : away_team) === winner
    },
    { 
      label: 'Shooting Efficiency',
      leader: breakdown.home.efg_pct > breakdown.away.efg_pct ? home_team : away_team,
      leaderColor: breakdown.home.efg_pct > breakdown.away.efg_pct ? homeColor : awayColor,
      diff: `+${efg_diff}%`,
      favorsWinner: (breakdown.home.efg_pct > breakdown.away.efg_pct ? home_team : away_team) === winner
    },
    { 
      label: 'Ball Security',
      leader: breakdown.home.tov_pct < breakdown.away.tov_pct ? home_team : away_team,
      leaderColor: breakdown.home.tov_pct < breakdown.away.tov_pct ? homeColor : awayColor,
      diff: `${tov_diff}% better`,
      favorsWinner: (breakdown.home.tov_pct < breakdown.away.tov_pct ? home_team : away_team) === winner
    },
    { 
      label: 'Rebounding',
      leader: breakdown.home.orb_pct > breakdown.away.orb_pct ? home_team : away_team,
      leaderColor: breakdown.home.orb_pct > breakdown.away.orb_pct ? homeColor : awayColor,
      diff: `+${orb_diff}%`,
      favorsWinner: (breakdown.home.orb_pct > breakdown.away.orb_pct ? home_team : away_team) === winner
    }
  ]

  return (
    <div className="card">
      <h2 className="card-header">Key Factors</h2>
      
      <div className="space-y-3">
        {factors.map((factor, index) => (
          <div 
            key={index} 
            className="flex items-center justify-between p-3 rounded border"
            style={{ 
              backgroundColor: factor.favorsWinner ? `${winnerColor}15` : 'transparent',
              borderColor: factor.favorsWinner ? winnerColor : '#404040'
            }}
          >
            <div className="flex-1">
              <div className="text-xs text-neutral-400 mb-1">{factor.label}</div>
              <div className="text-sm font-medium">
                <span style={{ color: factor.leaderColor }}>{factor.leader}</span>
                <span className="text-neutral-500 ml-2">{factor.diff}</span>
              </div>
            </div>
            <div>
              {factor.favorsWinner ? (
                <div className="w-2 h-2 rounded-full" style={{ backgroundColor: winnerColor }}></div>
              ) : (
                <div className="w-2 h-2 rounded-full bg-neutral-700"></div>
              )}
            </div>
          </div>
        ))}
      </div>

      <div className="mt-4 p-3 bg-neutral-900 border border-neutral-800 rounded text-xs text-neutral-400">
        Analysis based on recent performance trends and historical data. Predictions are probabilistic and subject to in-game variables.
      </div>
    </div>
  )
}

export default PredictionBreakdown