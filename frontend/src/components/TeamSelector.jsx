import React from 'react'
import { getTeamColor } from '../teamColors'

const TeamSelector = ({ label, teams, selectedTeam, onTeamChange, placeholder }) => {
  const teamColor = selectedTeam ? getTeamColor(selectedTeam) : '#FFFFFF'

  return (
    <div className="space-y-2">
      <label className="block text-sm font-semibold text-neutral-400 uppercase tracking-wide">
        {label}
      </label>
      <select
        value={selectedTeam}
        onChange={(e) => onTeamChange(e.target.value)}
        className="select-box"
        style={selectedTeam ? { borderColor: teamColor, borderWidth: '2px' } : {}}
      >
        <option value="">{placeholder}</option>
        {teams.map(team => (
          <option key={team} value={team}>
            {team}
          </option>
        ))}
      </select>
      
      {selectedTeam && (
        <div className="mt-3 p-3 rounded border" style={{ backgroundColor: `${teamColor}15`, borderColor: teamColor }}>
          <div className="text-sm">
            <span className="text-neutral-400">Selected:</span> 
            <span className="font-semibold ml-1" style={{ color: teamColor }}>{selectedTeam}</span>
          </div>
        </div>
      )}
    </div>
  )
}

export default TeamSelector