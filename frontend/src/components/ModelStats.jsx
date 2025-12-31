import React from 'react'
import { BiStats } from 'react-icons/bi'
import { FaChartLine, FaDatabase, FaBrain } from 'react-icons/fa'

const ModelStats = ({ modelStats }) => {
  return (
    <div className="space-y-6">
      {/* Overview Card */}
      <div className="card">
        <h2 className="card-header flex items-center gap-2">
          <BiStats className="text-nba-blue" />
          MODEL STATISTICS
        </h2>
        
        <div className="grid md:grid-cols-3 gap-6">
          <div className="text-center p-6 bg-gradient-to-br from-blue-900/30 to-blue-800/20 rounded-lg border border-blue-700">
            <FaChartLine className="text-5xl text-blue-400 mx-auto mb-3" />
            <div className="text-4xl font-bold text-blue-400">{modelStats.accuracy}%</div>
            <div className="text-gray-400 mt-2">Model Accuracy</div>
            <div className="text-sm text-gray-500 mt-1">Test Set Performance</div>
          </div>
          
          <div className="text-center p-6 bg-gradient-to-br from-green-900/30 to-green-800/20 rounded-lg border border-green-700">
            <FaDatabase className="text-5xl text-green-400 mx-auto mb-3" />
            <div className="text-4xl font-bold text-green-400">2,462</div>
            <div className="text-gray-400 mt-2">Total Games</div>
            <div className="text-sm text-gray-500 mt-1">Training + Test Data</div>
          </div>
          
          <div className="text-center p-6 bg-gradient-to-br from-purple-900/30 to-purple-800/20 rounded-lg border border-purple-700">
            <FaBrain className="text-5xl text-purple-400 mx-auto mb-3" />
            <div className="text-4xl font-bold text-purple-400">{modelStats.features}</div>
            <div className="text-gray-400 mt-2">Features Used</div>
            <div className="text-sm text-gray-500 mt-1">Statistical Inputs</div>
          </div>
        </div>
      </div>

      {/* Model Details */}
      <div className="card">
        <h2 className="card-header">MODEL DETAILS</h2>
        
        <div className="space-y-4">
          <div className="grid md:grid-cols-2 gap-4">
            <div className="p-4 bg-gray-700/50 rounded-lg">
              <div className="text-sm text-gray-400">Model Type</div>
              <div className="text-lg font-semibold mt-1">{modelStats.model_type}</div>
            </div>
            
            <div className="p-4 bg-gray-700/50 rounded-lg">
              <div className="text-sm text-gray-400">Training Season</div>
              <div className="text-lg font-semibold mt-1">2023-24 NBA Season</div>
            </div>
            
            <div className="p-4 bg-gray-700/50 rounded-lg">
              <div className="text-sm text-gray-400">Test Season</div>
              <div className="text-lg font-semibold mt-1">2024-25 NBA Season</div>
            </div>
            
            <div className="p-4 bg-gray-700/50 rounded-lg">
              <div className="text-sm text-gray-400">Last Updated</div>
              <div className="text-lg font-semibold mt-1">April 2025</div>
            </div>
          </div>
        </div>
      </div>

      {/* Features Used */}
      <div className="card">
        <h2 className="card-header">FEATURES USED IN PREDICTION</h2>
        
        <div className="grid md:grid-cols-2 gap-4">
          <div>
            <h3 className="text-lg font-semibold text-nba-blue mb-3">Four Factors</h3>
            <ul className="space-y-2">
              <li className="flex items-center gap-2">
                <div className="w-2 h-2 bg-blue-400 rounded-full"></div>
                <span>Offensive Rating (ORtg)</span>
              </li>
              <li className="flex items-center gap-2">
                <div className="w-2 h-2 bg-blue-400 rounded-full"></div>
                <span>Effective Field Goal % (eFG%)</span>
              </li>
              <li className="flex items-center gap-2">
                <div className="w-2 h-2 bg-blue-400 rounded-full"></div>
                <span>Turnover % (TOV%)</span>
              </li>
              <li className="flex items-center gap-2">
                <div className="w-2 h-2 bg-blue-400 rounded-full"></div>
                <span>Offensive Rebound % (ORB%)</span>
              </li>
            </ul>
          </div>
          
          <div>
            <h3 className="text-lg font-semibold text-purple-400 mb-3">Additional Factors</h3>
            <ul className="space-y-2">
              <li className="flex items-center gap-2">
                <div className="w-2 h-2 bg-purple-400 rounded-full"></div>
                <span>Injury Impact (Value-based)</span>
              </li>
              <li className="flex items-center gap-2">
                <div className="w-2 h-2 bg-purple-400 rounded-full"></div>
                <span>Injury Impact (Advanced Stats)</span>
              </li>
              <li className="flex items-center gap-2">
                <div className="w-2 h-2 bg-purple-400 rounded-full"></div>
                <span>Recent Performance Trends</span>
              </li>
            </ul>
          </div>
        </div>
      </div>

      {/* Performance Comparison */}
      <div className="card">
        <h2 className="card-header">PERFORMANCE COMPARISON</h2>
        
        <div className="space-y-4">
          <div>
            <div className="flex justify-between mb-2">
              <span>This Model</span>
              <span className="text-nba-blue font-semibold">{modelStats.accuracy}%</span>
            </div>
            <div className="w-full bg-gray-700 rounded-full h-4">
              <div 
                className="h-4 bg-gradient-to-r from-nba-blue to-blue-500 rounded-full"
                style={{ width: `${modelStats.accuracy}%` }}
              ></div>
            </div>
          </div>
          
          <div>
            <div className="flex justify-between mb-2">
              <span>Vegas Lines (Average)</span>
              <span className="text-yellow-500 font-semibold">~55%</span>
            </div>
            <div className="w-full bg-gray-700 rounded-full h-4">
              <div 
                className="h-4 bg-gradient-to-r from-yellow-600 to-yellow-500 rounded-full"
                style={{ width: '55%' }}
              ></div>
            </div>
          </div>
          
          <div>
            <div className="flex justify-between mb-2">
              <span>Advanced Analytics</span>
              <span className="text-green-500 font-semibold">~60-65%</span>
            </div>
            <div className="w-full bg-gray-700 rounded-full h-4">
              <div 
                className="h-4 bg-gradient-to-r from-green-600 to-green-500 rounded-full"
                style={{ width: '62.5%' }}
              ></div>
            </div>
          </div>
        </div>

        <div className="mt-6 p-4 bg-green-900/20 border border-green-700 rounded-lg">
          <div className="text-sm text-gray-300">
            <strong className="text-green-400">Competitive Performance:</strong> This model achieves 
            accuracy comparable to professional sports analytics platforms, demonstrating the effectiveness 
            of the Four Factors approach combined with injury impact analysis.
          </div>
        </div>
      </div>
    </div>
  )
}

export default ModelStats