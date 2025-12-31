import React from 'react'
import { getTeamColor } from '../teamColors'

const StatsComparison = ({ teamComparison }) => {
  if (!teamComparison || !teamComparison.stats) return null

  const { home_team, away_team, stats } = teamComparison
  const homeColor = getTeamColor(home_team)
  const awayColor = getTeamColor(away_team)

  return (
    <div className="card">
      <h2 className="card-header">Team Statistics</h2>
      
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b-2" style={{ borderColor: '#404040' }}>
              <th className="text-left py-3 px-4 text-neutral-400 font-medium uppercase tracking-wide text-sm">Metric</th>
              <th className="text-center py-3 px-4 font-semibold uppercase tracking-wide" style={{ color: homeColor }}>
                {home_team}
              </th>
              <th className="text-center py-3 px-4 font-semibold uppercase tracking-wide" style={{ color: awayColor }}>
                {away_team}
              </th>
              <th className="text-center py-3 px-4 text-neutral-400 font-medium uppercase tracking-wide text-sm">Edge</th>
            </tr>
          </thead>
          <tbody>
            {stats.map((stat, index) => (
              <tr key={index} className="table-row">
                <td className="py-3 px-4 font-medium text-neutral-300">{stat.metric}</td>
                <td className="text-center py-3 px-4 text-white font-medium">{stat.home}</td>
                <td className="text-center py-3 px-4 text-white font-medium">{stat.away}</td>
                <td className="text-center py-3 px-4 text-sm font-medium">
                  {stat.advantage === 'home' && (
                    <span style={{ color: homeColor }}>{home_team}</span>
                  )}
                  {stat.advantage === 'away' && (
                    <span style={{ color: awayColor }}>{away_team}</span>
                  )}
                  {stat.advantage === 'even' && (
                    <span className="text-neutral-600">—</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default StatsComparison