import React from 'react';
import { ExtractionStatistics } from '../types/extraction';
import { Hash, Table, Sigma } from 'lucide-react';

interface StatisticsProps {
  stats: ExtractionStatistics;
}

export const Statistics: React.FC<StatisticsProps> = ({ stats }) => {
  const statItems = [
    {
      label: 'Pages',
      value: stats.total_pages,
      icon: Hash,
      color: 'text-indigo-400',
      bg: 'bg-indigo-500/10',
    },
    {
      label: 'Tables Extracted',
      value: stats.tables_count,
      icon: Table,
      color: 'text-blue-400',
      bg: 'bg-blue-500/10',
    },
    {
      label: 'Formulas / Math',
      value: stats.formulas_count,
      icon: Sigma,
      color: 'text-rose-400',
      bg: 'bg-rose-500/10',
    },
  ];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
      {statItems.map((item, idx) => {
        const IconComponent = item.icon;
        return (
          <div
            key={idx}
            className="bg-slate-900 border border-slate-800/80 rounded-2xl p-4 flex items-center space-x-3.5 shadow-md hover:border-slate-700 transition"
          >
            <div className={`p-3 rounded-xl ${item.bg} ${item.color} flex-shrink-0`}>
              <IconComponent className="w-5 h-5" />
            </div>
            <div className="min-w-0">
              <p className="text-xl font-bold text-slate-100 leading-none">{item.value}</p>
              <p className="text-xs font-medium text-slate-400 truncate mt-1.5">{item.label}</p>
            </div>
          </div>
        );
      })}
    </div>
  );
};
