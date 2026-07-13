import React from 'react';

type ColumnDef<T> = {
  header: string;
  accessorKey: keyof T;
};

interface DataTableProps<T> {
  data: T[];
  columns: ColumnDef<T>[];
  title: string;
}

export function DataTable<T>({ data, columns, title }: DataTableProps<T>) {
  if (!data || data.length === 0) {
    return <div className="p-4 border rounded-xl shadow-sm bg-white/50 backdrop-blur">No data available for {title}</div>;
  }

  return (
    <div className="w-full bg-white/70 backdrop-blur shadow-lg rounded-xl overflow-hidden border border-gray-100">
      <div className="px-6 py-4 border-b border-gray-100 bg-gray-50/50">
        <h3 className="text-lg font-semibold text-gray-800">{title}</h3>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-gray-50/80 text-gray-600 uppercase text-xs tracking-wider">
              {columns.map((col, idx) => (
                <th key={idx} className="px-6 py-4 font-medium border-b border-gray-100">{col.header}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 text-sm">
            {data.map((row, rIdx) => (
              <tr key={rIdx} className="hover:bg-blue-50/50 transition-colors">
                {columns.map((col, cIdx) => (
                  <td key={cIdx} className="px-6 py-4 text-gray-700 whitespace-nowrap">
                    {String(row[col.accessorKey] ?? '')}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
