"use client";

import React, { useEffect, useState } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, Legend, ResponsiveContainer, AreaChart, Area } from 'recharts';
import { DataTable } from '@/components/DataTable';
import SpeechToText from '@/components/SpeechToText';
import { Search, Activity, Package, Shield, Phone } from 'lucide-react';

type DashboardData = {
  medicines: any[];
  inventory: any[];
  suppliers: any[];
  contracts: any[];
};

export default function Dashboard() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [forecast, setForecast] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('overview');
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    async function fetchData() {
      try {
        const [dashRes, forecastRes] = await Promise.all([
          fetch('http://localhost:5001/api/dashboard'),
          fetch('http://localhost:5001/api/forecast')
        ]);
        const dashData = await dashRes.json();
        const forecastData = await forecastRes.json();
        
        setData(dashData);
        setForecast(forecastData);
      } catch (err) {
        console.error("Failed to fetch dashboard data:", err);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);

  const handleSpeechInput = (text: string) => {
    setSearchQuery((prev) => prev + (prev ? ' ' : '') + text);
  };

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-gray-50">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-purple-600"></div>
      </div>
    );
  }

  const filteredInventory = data?.inventory.filter((item: any) => 
    item.name.toLowerCase().includes(searchQuery.toLowerCase()) || 
    item.location.toLowerCase().includes(searchQuery.toLowerCase())
  ) || [];

  return (
    <div className="min-h-screen bg-gray-50 text-gray-900 font-sans">
      {/* Top Navigation */}
      <header className="bg-white/80 backdrop-blur-md shadow-sm border-b border-gray-200 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="bg-purple-600 p-2 rounded-lg shadow-inner">
              <Shield className="text-white" size={24} />
            </div>
            <h1 className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-purple-700 to-indigo-600">
              Defense Medical Command
            </h1>
          </div>
          
          <div className="flex items-center space-x-4 w-1/3">
            <div className="relative w-full flex items-center">
              <Search className="absolute left-3 text-gray-400" size={18} />
              <input
                type="text"
                placeholder="Search inventory..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-12 py-2 bg-gray-100 border-transparent focus:bg-white focus:border-purple-500 focus:ring-2 focus:ring-purple-200 rounded-full transition-all"
              />
              <div className="absolute right-1">
                <SpeechToText onTranscript={handleSpeechInput} />
              </div>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        
        {/* KPI Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <KpiCard title="Total Medicines" value={data?.medicines.length || 0} icon={<Activity />} color="text-emerald-600" bg="bg-emerald-100" />
          <KpiCard title="Total Stock Units" value={data?.inventory.reduce((acc, curr) => acc + curr.stock, 0) || 0} icon={<Package />} color="text-purple-600" bg="bg-purple-100" />
          <KpiCard title="Active Contracts" value={data?.contracts.length || 0} icon={<Shield />} color="text-indigo-600" bg="bg-indigo-100" />
          <KpiCard title="Registered Suppliers" value={data?.suppliers.length || 0} icon={<Phone />} color="text-orange-600" bg="bg-orange-100" />
        </div>

        {/* Tabs */}
        <div className="flex space-x-1 bg-gray-200/50 p-1 rounded-xl w-fit">
          {['overview', 'inventory', 'suppliers', 'contracts'].map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-6 py-2 rounded-lg text-sm font-medium transition-all ${
                activeTab === tab 
                  ? 'bg-white text-purple-700 shadow-sm' 
                  : 'text-gray-600 hover:text-gray-900 hover:bg-white/50'
              }`}
            >
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        <div className="transition-all">
          {activeTab === 'overview' && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              {/* Forecast Chart */}
              <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100">
                <h3 className="text-lg font-semibold text-gray-800 mb-6">30-Day Stock Level Forecast</h3>
                <div className="h-72">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={forecast} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                      <defs>
                        <linearGradient id="colorStock" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.3}/>
                          <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0}/>
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                      <XAxis dataKey="date" tick={{fontSize: 12}} tickLine={false} axisLine={false} />
                      <YAxis tick={{fontSize: 12}} tickLine={false} axisLine={false} />
                      <RechartsTooltip 
                        contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                      />
                      <Area type="monotone" dataKey="stock_level" stroke="#8b5cf6" fillOpacity={1} fill="url(#colorStock)" strokeWidth={3} />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Consumption Chart */}
              <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100">
                <h3 className="text-lg font-semibold text-gray-800 mb-6">Predicted Consumption</h3>
                <div className="h-72">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={forecast} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                      <XAxis dataKey="date" tick={{fontSize: 12}} tickLine={false} axisLine={false} />
                      <YAxis tick={{fontSize: 12}} tickLine={false} axisLine={false} />
                      <RechartsTooltip 
                        contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                      />
                      <Line type="monotone" dataKey="predicted_consumption" stroke="#f43f5e" strokeWidth={3} dot={false} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'inventory' && (
            <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
              <DataTable 
                title="Current Stock Values"
                data={filteredInventory}
                columns={[
                  { header: "Med ID", accessorKey: "id" },
                  { header: "Medicine Name", accessorKey: "name" },
                  { header: "Quantity Available", accessorKey: "stock" },
                  { header: "Location", accessorKey: "location" }
                ]}
              />
            </div>
          )}

          {activeTab === 'suppliers' && (
            <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
              <DataTable 
                title="Registered Suppliers"
                data={data?.suppliers || []}
                columns={[
                  { header: "Supplier ID", accessorKey: "id" },
                  { header: "Supplier Name", accessorKey: "name" },
                  { header: "Contact Email", accessorKey: "email" },
                  { header: "Phone No.", accessorKey: "phone" }
                ]}
              />
            </div>
          )}

          {activeTab === 'contracts' && (
            <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
              <DataTable 
                title="Active Contracts"
                data={data?.contracts || []}
                columns={[
                  { header: "Contract No", accessorKey: "contractNo" },
                  { header: "Supplier", accessorKey: "supplier" },
                  { header: "Medicine", accessorKey: "medicine" },
                  { header: "Agreed Rate ($)", accessorKey: "rate" }
                ]}
              />
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

function KpiCard({ title, value, icon, color, bg }: { title: string, value: string | number, icon: React.ReactNode, color: string, bg: string }) {
  return (
    <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100 flex items-center space-x-4 hover:shadow-md transition-shadow">
      <div className={`p-4 rounded-xl ${bg} ${color}`}>
        {icon}
      </div>
      <div>
        <p className="text-sm font-medium text-gray-500">{title}</p>
        <p className="text-2xl font-bold text-gray-900">{value}</p>
      </div>
    </div>
  );
}
