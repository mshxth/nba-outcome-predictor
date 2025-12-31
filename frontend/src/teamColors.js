export const TEAM_COLORS = {
    'Atlanta': { primary: '#E03A3E', secondary: '#C1D32F' },
    'Boston': { primary: '#007A33', secondary: '#BA9653' },
    'Brooklyn': { primary: '#000000', secondary: '#FFFFFF' },
    'Charlotte': { primary: '#1D1160', secondary: '#00788C' },
    'Chicago': { primary: '#CE1141', secondary: '#000000' },
    'Cleveland': { primary: '#860038', secondary: '#041E42' },
    'Dallas': { primary: '#00538C', secondary: '#002B5E' },
    'Denver': { primary: '#0E2240', secondary: '#FEC524' },
    'Detroit': { primary: '#C8102E', secondary: '#1D42BA' },
    'Golden State': { primary: '#1D428A', secondary: '#FFC72C' },
    'Houston': { primary: '#CE1141', secondary: '#000000' },
    'Indiana': { primary: '#002D62', secondary: '#FDBB30' },
    'LA Clippers': { primary: '#C8102E', secondary: '#1D428A' },
    'LA Lakers': { primary: '#552583', secondary: '#FDB927' },
    'Memphis': { primary: '#5D76A9', secondary: '#12173F' },
    'Miami': { primary: '#98002E', secondary: '#F9A01B' },
    'Milwaukee': { primary: '#00471B', secondary: '#EEE1C6' },
    'Minnesota': { primary: '#0C2340', secondary: '#236192' },
    'New Orleans': { primary: '#0C2340', secondary: '#C8102E' },
    'New York': { primary: '#006BB6', secondary: '#F58426' },
    'Oklahoma City': { primary: '#007AC1', secondary: '#EF3B24' },
    'Orlando': { primary: '#0077C0', secondary: '#C4CED4' },
    'Philadelphia': { primary: '#006BB6', secondary: '#ED174C' },
    'Phoenix': { primary: '#1D1160', secondary: '#E56020' },
    'Portland': { primary: '#E03A3E', secondary: '#000000' },
    'Sacramento': { primary: '#5A2D81', secondary: '#63727A' },
    'San Antonio': { primary: '#C4CED4', secondary: '#000000' },
    'Toronto': { primary: '#CE1141', secondary: '#000000' },
    'Utah': { primary: '#002B5C', secondary: '#F9A01B' },
    'Washington': { primary: '#002B5C', secondary: '#E31837' }
  }
  
  export const getTeamColor = (teamName) => {
    return TEAM_COLORS[teamName]?.primary || '#FFFFFF'
  }
  
  export const getTeamSecondaryColor = (teamName) => {
    return TEAM_COLORS[teamName]?.secondary || '#999999'
  }