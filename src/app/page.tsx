"use client";

import { Send, X, FileText, Activity, AlertTriangle, Pill, FileSignature, Building2, Shield, User, ArrowLeft, Edit, Trash2, Download, Upload, Search, SlidersHorizontal } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, LineChart, Line } from 'recharts';
import SpeechToText from '../components/SpeechToText';

const schemaToApiMap: Record<string, Record<string, string>> = {
  medicines: {
    hstnumItembrandId: 'id',
    gnumHospitalCode: 'hospital_code',
    hstnumItemId: 'item_id',
    hststrItemName: 'name',
    hstnumManufacturerId: 'manufacturer_id',
    hstnumDefaultRate: 'default_rate',
    hstnumRateUnitId: 'rate_unit_id',
    hstnumApprovedType: 'approved_type',
    hststrSpecification: 'specification',
    hstnumItemMake: 'item_make',
    gdtEffectiveFrm: 'effective_from',
    hststrVedCategory: 'ved_category',
  },
  inventory: {
    hstnumInventoryId: 'id',
    gnumHospitalCode: 'hospital_code',
    hstnumItemId: 'item_id',
    hstnumItembrandId: 'itembrand_id',
    hstnumStockQty: 'quantity',
    hstnumMinStockLevel: 'min_stock',
    hstnumMaxStockLevel: 'max_stock',
    hstdtExpiryDate: 'expiry_date',
    hststrBatchNo: 'batch_no',
  },
  contracts: {
    hstnumRcId: 'id',
    gnumHospitalCode: 'hospital_code',
    hstnumIsApproval: 'is_approval',
    hstnumContractTypeId: 'contract_type_id',
    hstnumItemId: 'item_id',
    hstnumItembrandId: 'itembrand_id',
    hststrTenderNo: 'tender_no',
    hststrQuotationNo: 'quotation_no',
    hstnumSupplierId: 'supplier_id',
    hstnumRate: 'rate',
  },
  hospitals: {
    gnumHospitalCode: 'id',
    gstrHospitalName: 'name',
    gstrHospitalAddress: 'address',
    gnumContactNo: 'contact_no',
  },
  suppliers: {
    supplier_id: 'id',
    supplier_name: 'name',
    email: 'email',
    contact_no: 'contact_no',
    address: 'address',
  }
};

type Message = {
  id: string;
  role: "user" | "bot";
  content: string;
};

const ExpandableChart = ({ payload }: { payload: any }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [mounted, setMounted] = useState(false);
  
  const isLegacy = Array.isArray(payload);
  const data = isLegacy ? payload : payload.data || [];
  const rawChartType = (isLegacy ? 'bar' : payload.chartType || 'bar').toLowerCase();
  let chartType = 'bar';
  if (rawChartType.includes('pie')) chartType = 'pie';
  if (rawChartType.includes('line')) chartType = 'line';

  // Dynamic Keys Extraction
  const dataKeys = data.length > 0 ? Object.keys(data[0]) : [];
  
  // Find X-Axis Key (Look for 'name' or 'date' or anything that is a string, defaulting to 'name')
  let xAxisKey = 'name';
  if (data.length > 0) {
    const possibleX = dataKeys.find(k => k.toLowerCase() === 'name' || k.toLowerCase() === 'date' || typeof data[0][k] === 'string');
    if (possibleX) xAxisKey = possibleX;
  }

  // Find Y-Axis Keys (All numeric fields)
  let yAxisKeys = dataKeys.filter(k => k !== xAxisKey && typeof data[0][k] === 'number');
  if (yAxisKeys.length === 0) yAxisKeys = ['value']; // fallback

  useEffect(() => {
    setMounted(true);
  }, []);

  const COLORS = ['#1a365d', '#b54a39', '#eab308', '#22c55e', '#a855f7', '#ec4899', '#0ea5e9', '#f97316', '#64748b', '#14b8a6'];

  const renderCustomizedLabel = (props: any) => {
    const { cx, cy, x, y, outerRadius, value, index, payload } = props;
    
    // Initialize collision track on index 0
    if (index === 0) {
      (window as any).lastYLeft = null;
      (window as any).lastYRight = null;
    }
    
    // Return early if Recharts position is undefined or NaN
    if (x === undefined || y === undefined || isNaN(x) || isNaN(y)) {
      return null;
    }

    const dx = x - cx;
    const dy = y - cy;
    const dist = Math.sqrt(dx * dx + dy * dy) || 1;
    const cos = dx / dist;
    const sin = dy / dist;
    
    // Calculate start, bend, and end points of connector line mathematically
    const sx = cx + outerRadius * cos;
    const sy = cy + outerRadius * sin;
    const px = cx + (outerRadius + 15) * cos;
    const py = cy + (outerRadius + 15) * sin;
    
    const isRight = x > cx;
    let targetY = y;
    const minSpacing = 16; // minimum pixels between labels to prevent overlapping
    
    if (isRight) {
      if ((window as any).lastYRight !== null && (targetY - (window as any).lastYRight) < minSpacing) {
        targetY = (window as any).lastYRight + minSpacing;
      }
      (window as any).lastYRight = targetY;
    } else {
      if ((window as any).lastYLeft !== null && (targetY - (window as any).lastYLeft) < minSpacing) {
        targetY = (window as any).lastYLeft + minSpacing;
      }
      (window as any).lastYLeft = targetY;
    }

    const textX = isRight ? px + 8 : px - 8;
    const textAnchor = isRight ? 'start' : 'end';
    const name = payload && payload.name ? payload.name : '';
    const labelText = `${name}: ${value}`;

    return (
      <g>
        <path 
          d={`M${sx},${sy} L${px},${targetY} L${isRight ? px + 5 : px - 5},${targetY}`} 
          stroke="#9ca3af" 
          fill="none" 
          strokeWidth={1} 
        />
        <text 
          x={textX} 
          y={targetY} 
          fill="#374151" 
          textAnchor={textAnchor} 
          fontSize={10} 
          dominantBaseline="central"
        >
          {labelText}
        </text>
      </g>
    );
  };

  const renderChart = (expanded: boolean) => {
    if (chartType === 'pie') {
      return (
        <PieChart margin={{ top: 40, right: 40, left: 40, bottom: 40 }}>
          <Pie 
            data={data} 
            dataKey={yAxisKeys[0]} 
            nameKey={xAxisKey} 
            cx="50%" 
            cy="50%" 
            outerRadius={expanded ? 220 : 80} 
            label={expanded ? renderCustomizedLabel : false}
          >
            {data.map((entry: any, index: number) => (
              <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip contentStyle={{fontSize: '12px'}} />
        </PieChart>
      );
    } else if (chartType === 'line') {
      return (
        <LineChart data={data} margin={{ top: 30, right: 10, left: -20, bottom: expanded ? 120 : 90 }}>
          <XAxis 
            dataKey={xAxisKey} 
            tick={{fontSize: expanded ? 12 : 10, angle: -90, textAnchor: 'end'}} 
            interval={0} 
            tickFormatter={(value) => value && String(value).length > 15 ? String(value).substring(0, 15) + '...' : value}
          />
          <YAxis tick={{fontSize: 10}} />
          <Tooltip contentStyle={{fontSize: '12px'}} />
          {yAxisKeys.map((key, index) => (
             <Line key={key} type="monotone" dataKey={key} stroke={COLORS[index % COLORS.length]} strokeWidth={3} dot={{r: 4}} />
          ))}
        </LineChart>
      );
    } else {
      return (
        <BarChart data={data} margin={{ top: 30, right: 10, left: -20, bottom: expanded ? 120 : 90 }}>
          <XAxis 
            dataKey={xAxisKey} 
            tick={{fontSize: expanded ? 12 : 10, angle: -90, textAnchor: 'end'}} 
            interval={0} 
            tickFormatter={(value) => value && String(value).length > 15 ? String(value).substring(0, 15) + '...' : value}
          />
          <YAxis tick={{fontSize: 10}} />
          <Tooltip contentStyle={{fontSize: '12px'}} cursor={{fill: '#f1f4f9'}} />
          {yAxisKeys.map((key, index) => (
             <Bar key={key} dataKey={key} fill={COLORS[index % COLORS.length]} radius={[4,4,0,0]} />
          ))}
        </BarChart>
      );
    }
  };

  if (!mounted) {
    return <div className="w-full h-72 bg-gray-50 animate-pulse rounded-lg border border-gray-200 flex items-center justify-center text-xs text-gray-400">Loading visualization...</div>;
  }

  const renderChartContainer = (expanded: boolean) => {
    if (expanded) {
      return (
        <div style={{ width: chartType === 'pie' ? 1000 : Math.max(data.length * 100, 800), height: 700, margin: '0 auto' }}>
          <ResponsiveContainer width="100%" height={650}>
            {renderChart(expanded)}
          </ResponsiveContainer>
        </div>
      );
    }
    return (
      <div style={{ width: chartType === 'pie' ? '100%' : Math.max(data.length * 60, 400), height: '100%' }}>
        <ResponsiveContainer width="100%" height={240}>
          {renderChart(expanded)}
        </ResponsiveContainer>
      </div>
    );
  };

  return (
    <>
      <div className="w-full mt-4 bg-white p-2 rounded-lg border border-gray-200 shadow-sm overflow-x-auto overflow-y-hidden custom-scrollbar relative h-72">
        <button onClick={() => setIsExpanded(true)} className="absolute top-2 right-2 z-10 text-xs bg-gray-100 hover:bg-gray-200 text-gray-700 px-2 py-1 rounded shadow-sm border border-gray-300">
          ⛶ Expand
        </button>
        {renderChartContainer(false)}
      </div>

      {isExpanded && mounted && createPortal(
        <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/60 backdrop-blur-sm p-8">
          <div className="bg-white rounded-xl shadow-2xl w-full h-full max-w-7xl max-h-[80vh] flex flex-col overflow-hidden relative">
            <div className="p-4 bg-gray-100 border-b flex justify-between items-center">
              <h2 className="text-lg font-bold text-[#1a365d]">Data Visualization</h2>
              <button onClick={() => setIsExpanded(false)} className="px-4 py-2 bg-[#b54a39] text-white rounded shadow hover:bg-red-700 transition">
                Close
              </button>
            </div>
            <div className="flex-1 p-6 overflow-auto custom-scrollbar">
              <div className="py-12 flex justify-center">
                {renderChartContainer(true)}
              </div>
            </div>
          </div>
        </div>,
        document.body
      )}
    </>
  );
};

const MemoizedMarkdownComponents = {
  pre({ children, ...props }: any) {
    const codeChild = children && children.props;
    const codeText = codeChild && codeChild.children ? String(codeChild.children).trim() : '';
    const isChart = codeChild && (
      (codeChild.className && codeChild.className.includes('language-chart')) ||
      (codeText.startsWith('chart') && codeText.includes('chartType'))
    );
    if (isChart) {
      return <>{children}</>;
    }
    return <pre {...props}>{children}</pre>;
  },
  code({node, inline, className, children, ...props}: any) {
    console.log("[react-markdown code] className:", className, "has children:", !!children);
    let text = String(children).trim();
    const match = /language-(\w+)/.exec(className || '');
    
    const isChartClass = match && match[1] === 'chart';
    const isChartContent = text.startsWith('chart') && text.includes('chartType');
    
    if (isChartClass || isChartContent) {
      try {
         console.log("[react-markdown code] detected chart block with text length:", text.length);
         if (text.startsWith('chart')) {
           text = text.substring(5).trim();
         }
         if (text.startsWith('```json')) text = text.substring(7);
         if (text.startsWith('```')) text = text.substring(3);
         if (text.endsWith('```')) text = text.substring(0, text.length - 3);
         text = text.trim();
         
         const payload = new Function("return " + text)();
         return <ExpandableChart payload={payload} />;
      } catch (e: any) {
         console.error("[react-markdown code] chart parsing failed:", e.message);
         return (
           <div className="text-red-500 text-xs mt-2 border p-2 bg-red-50">
             Error parsing chart data: {e.message}
             <pre className="mt-2 text-[10px] overflow-auto max-h-32 text-gray-700">{String(children)}</pre>
           </div>
         );
      }
    }
    return <code className={className} {...props}>{children}</code>
  }
};

export default function ChatWidgetPage() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [localInput, setLocalInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [lang, setLang] = useState("EN");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [activeModal, setActiveModal] = useState<"about" | "how-to-use" | "login" | "add-table" | null>(null);
  const [loginView, setLoginView] = useState<"login" | "signup">("login");
  const [captchaCode, setCaptchaCode] = useState("");
  const [captchaInput, setCaptchaInput] = useState("");
  const [signupPassword, setSignupPassword] = useState("");
  const [signupEmail, setSignupEmail] = useState("");
  const [signupUsername, setSignupUsername] = useState("");
  const [loginUsername, setLoginUsername] = useState("");
  const [loginPassword, setLoginPassword] = useState("");
  const [loginSector, setLoginSector] = useState("central");
  const [signupSector, setSignupSector] = useState("central");
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [officerInfo, setOfficerInfo] = useState<{ username: string; sector: string; email: string } | null>(null);
  const [activeTab, setActiveTab] = useState<string>("overview");
  const [tables, setTables] = useState<{ db_name: string; name: string }[]>([]);
  const [tableColumns, setTableColumns] = useState<{ name: string; type: string }[]>([]);
  const [activeTableDbName, setActiveTableDbName] = useState("");
  const [tableData, setTableData] = useState<any[]>([]);
  const [tableLoading, setTableLoading] = useState(false);
  const [crudModal, setCrudModal] = useState<"add" | "edit" | null>(null);
  const [selectedRow, setSelectedRow] = useState<any | null>(null);
  const [formData, setFormData] = useState<any>({});
  const [newTableName, setNewTableName] = useState("");

  const [selectedRowIds, setSelectedRowIds] = useState<number[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [sortField, setSortField] = useState("");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("asc");

  const getTableColor = (name: string) => {
    const lower = name.toLowerCase();
    if (lower.includes("medicine")) {
      return {
        bg: '#166534', // Rich forest green
        color: '#ffffff',
        shadow: 'rgba(22, 101, 52, 0.4)'
      };
    }
    if (lower.includes("inventory")) {
      return {
        bg: '#f97316', // Orange
        color: '#ffffff',
        shadow: 'rgba(249, 115, 22, 0.4)'
      };
    }
    if (lower.includes("contract")) {
      return {
        bg: '#582a58', // Deep eggplant purple
        color: '#ffffff',
        shadow: 'rgba(88, 42, 88, 0.4)'
      };
    }
    if (lower.includes("hospital")) {
      return {
        bg: '#1e3a8a', // Navy blue
        color: '#ffffff',
        shadow: 'rgba(30, 58, 138, 0.4)'
      };
    }
    if (lower.includes("supplier")) {
      return {
        bg: '#e11d48', // Rose
        color: '#ffffff',
        shadow: 'rgba(225, 29, 72, 0.4)'
      };
    }
    return {
      bg: '#0ea5e9', // Sky blue for dynamic tables
      color: '#ffffff',
      shadow: 'rgba(14, 165, 233, 0.4)'
    };
  };

  const getProcessedData = () => {
    let data = [...tableData];
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim();
      data = data.filter(row => {
        return Object.entries(row).some(([key, val]) => {
          if (val === null || val === undefined) return false;
          return String(val).toLowerCase().includes(q);
        });
      });
    }
    if (sortField) {
      data.sort((a, b) => {
        let valA = a[sortField];
        let valB = b[sortField];
        if (valA === null || valA === undefined) valA = '';
        if (valB === null || valB === undefined) valB = '';
        
        if (typeof valA === 'number' && typeof valB === 'number') {
          return sortOrder === 'asc' ? valA - valB : valB - valA;
        }
        
        const strA = String(valA).toLowerCase();
        const strB = String(valB).toLowerCase();
        if (strA < strB) return sortOrder === 'asc' ? -1 : 1;
        if (strA > strB) return sortOrder === 'asc' ? 1 : -1;
        return 0;
      });
    }
    return data;
  };

  const generateCaptcha = () => {
    const chars = "ABCDEFGHJKLMNOPQRSTUVWXYZ23456789";
    let code = "";
    for (let i = 0; i < 6; i++) {
      code += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    setCaptchaCode(code);
    setCaptchaInput("");
  };

  useEffect(() => {
    if (activeModal === 'login') {
      generateCaptcha();
      setLoginView('login');
      setSignupPassword("");
      setSignupEmail("");
      setSignupUsername("");
      setLoginUsername("");
      setLoginPassword("");
      setLoginSector("");
      setSignupSector("");
    }
  }, [activeModal]);

  const isLengthValid = signupPassword.length >= 8;
  const hasUppercase = /[A-Z]/.test(signupPassword);
  const hasNumber = /[0-9]/.test(signupPassword);
  const hasSpecial = /[^A-Za-z0-9]/.test(signupPassword);
  const isPasswordStrong = isLengthValid && hasUppercase && hasNumber && hasSpecial;

  const handleLoginSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (captchaInput.toUpperCase() !== captchaCode) {
      alert("Verification failed: Invalid CAPTCHA code! Please try again.");
      generateCaptcha();
      return;
    }
    
    try {
      const res = await fetch('http://localhost:5001/api/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sector: loginSector,
          username: loginUsername,
          password: loginPassword
        })
      });
      
      const data = await res.json();
      if (!res.ok) {
        alert(`Authentication Error: ${data.error}`);
        return;
      }
      
      setIsLoggedIn(true);
      setOfficerInfo(data.officer);
      setActiveTab("overview");
      setIsOpen(false);
      setActiveModal(null);
      alert(`Success: ${data.success}! Welcome, Officer ${data.officer.username} (${data.officer.sector} Command).`);
    } catch (err) {
      console.error(err);
      alert('Failed to connect to authentication server. Please check that app.py backend is running.');
    }
  };

  const handleSignupSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isPasswordStrong) {
      alert("Validation failed: Please ensure your password meets all strength requirements.");
      return;
    }
    if (captchaInput.toUpperCase() !== captchaCode) {
      alert("Verification failed: Invalid CAPTCHA code! Please try again.");
      generateCaptcha();
      return;
    }
    
    try {
      const res = await fetch('http://localhost:5001/api/signup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sector: signupSector,
          email: signupEmail,
          username: signupUsername,
          password: signupPassword
        })
      });
      
      const data = await res.json();
      if (!res.ok) {
        alert(`Registration Error: ${data.error}`);
        return;
      }
      
      alert(`Success: ${data.success}! Switch to Login to authenticate.`);
      setLoginView('login');
      generateCaptcha();
    } catch (err) {
      console.error(err);
      alert('Failed to connect to authentication server. Please check that app.py backend is running.');
    }
  };

  const fetchTableData = async (tabName: string) => {
    if (tabName === 'overview') return;
    setTableLoading(true);
    try {
      const res = await fetch(`http://localhost:5001/api/data/${tabName}`);
      const data = await res.json();
      if (res.ok) {
        setTableData(data);
      } else {
        alert(`Error loading data: ${data.error}`);
      }
    } catch (err) {
      console.error(err);
      alert('Failed to connect to backend server.');
    } finally {
      setTableLoading(false);
    }
  };

  const fetchTablesList = async () => {
    try {
      const res = await fetch('http://localhost:5001/api/tables');
      const data = await res.json();
      if (res.ok) {
        setTables(data);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const fetchTableColumns = async (tabName: string) => {
    try {
      const res = await fetch(`http://localhost:5001/api/columns/${tabName}`);
      const data = await res.json();
      if (res.ok) {
        setTableColumns(data);
      }
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    const initTables = async () => {
      try {
        const res = await fetch('http://localhost:5001/api/tables');
        const data = await res.json();
        if (res.ok) {
          setTables(data);
          setActiveTab("");
          setActiveTableDbName("");
        }
      } catch (err) {
        console.error(err);
      }
    };
    if (isLoggedIn) {
      initTables();
    }
  }, [isLoggedIn]);

  useEffect(() => {
    if (isLoggedIn && activeTab && activeTab !== 'overview') {
      fetchTableData(activeTab);
      fetchTableColumns(activeTab);
      setSelectedRowIds([]);
      setSearchQuery("");
      setSortField("");
    }
  }, [activeTab, isLoggedIn]);

  const handleCreateTable = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTableName.trim()) return;
    try {
      const res = await fetch('http://localhost:5001/api/table/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ table_name: newTableName })
      });
      const data = await res.json();
      if (res.ok) {
        alert(data.success);
        setNewTableName("");
        setActiveModal(null);
        fetchTablesList();
      } else {
        alert(`Error: ${data.error}`);
      }
    } catch (err) {
      console.error(err);
      alert('Failed to connect to backend server.');
    }
  };

  const handleDeleteRow = async (rowId: number) => {
    if (!confirm("Are you sure you want to delete this row permanently?")) return;
    try {
      const res = await fetch(`http://localhost:5001/api/data/${activeTab}/${rowId}`, {
        method: 'DELETE'
      });
      const data = await res.json();
      if (res.ok) {
        alert("Row deleted successfully!");
        fetchTableData(activeTab);
      } else {
        alert(`Error: ${data.error}`);
      }
    } catch (err) {
      console.error(err);
      alert('Failed to connect to backend server.');
    }
  };

  const handleExportCSV = () => {
    if (tableData.length === 0) return;
    const headers = Object.keys(tableData[0]).join(",");
    const rows = tableData.map(row => 
      Object.values(row).map(val => `"${String(val ?? '').replace(/"/g, '""')}"`).join(",")
    );
    const csvContent = "data:text/csv;charset=utf-8," + [headers, ...rows].join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `${activeTab}_export.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleImportCSV = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = async (event) => {
      try {
        const text = event.target?.result as string;
        const lines = text.split("\n").map(l => l.trim()).filter(Boolean);
        if (lines.length < 2) return;
        const headers = lines[0].split(",").map(h => h.trim().replace(/^"|"$/g, ''));
        
        // Dynamic CSV header validation check
        const map = schemaToApiMap[activeTab];
        const expectedKeys = map 
          ? Object.values(map) 
          : tableColumns.map(col => col.name);
          
        const hasOverlap = headers.some(h => expectedKeys.includes(h));
        if (!hasOverlap) {
          alert(`Import failed: CSV headers do not match this table.\n\nExpected headers: ${expectedKeys.join(', ')}`);
          return;
        }

        const newRows = lines.slice(1).map(line => {
          const values = line.split(",").map(v => v.trim().replace(/^"|"$/g, ''));
          const rowObj: any = {};
          headers.forEach((h, idx) => {
            rowObj[h] = values[idx] || '';
          });
          return rowObj;
        });
        let successCount = 0;
        for (const row of newRows) {
          const res = await fetch(`http://localhost:5001/api/data/${activeTab}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(row)
          });
          if (res.ok) successCount++;
        }
        alert(`Successfully imported ${successCount} records!`);
        fetchTableData(activeTab);
      } catch (err) {
        console.error(err);
        alert("Failed to parse CSV file.");
      }
    };
    reader.readAsText(file);
    e.target.value = '';
  };

  const handleDeleteSelected = async () => {
    if (selectedRowIds.length === 0) return;
    if (!confirm(`Are you sure you want to delete the ${selectedRowIds.length} selected records?`)) return;
    try {
      let successCount = 0;
      for (const id of selectedRowIds) {
        const res = await fetch(`http://localhost:5001/api/data/${activeTab}/${id}`, {
          method: 'DELETE'
        });
        if (res.ok) successCount++;
      }
      alert(`Successfully deleted ${successCount} records.`);
      setSelectedRowIds([]);
      fetchTableData(activeTab);
    } catch (err) {
      console.error(err);
    }
  };

  const handleCrudSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const isEdit = crudModal === 'edit';
    const url = isEdit 
      ? `http://localhost:5001/api/data/${activeTab}/${selectedRow.id}`
      : `http://localhost:5001/api/data/${activeTab}`;
      
    try {
      const payload: any = {};
      const map = schemaToApiMap[activeTab];
      if (map) {
        tableColumns.forEach(col => {
          const apiKey = map[col.name] || col.name;
          payload[apiKey] = formData[col.name];
        });
      } else {
        Object.assign(payload, formData);
      }

      const res = await fetch(url, {
        method: isEdit ? 'PUT' : 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (res.ok) {
        alert(isEdit ? "Record updated successfully!" : "Record added successfully!");
        setCrudModal(null);
        setSelectedRow(null);
        setFormData({});
        fetchTableData(activeTab);
      } else {
        alert(`Error: ${data.error}`);
      }
    } catch (err) {
      console.error(err);
      alert('Failed to connect to backend server.');
    }
  };

  const openEditModal = (row: any) => {
    setSelectedRow(row);
    const mappedData: any = {};
    const map = schemaToApiMap[activeTab];
    if (map) {
      tableColumns.forEach(col => {
        const apiKey = map[col.name] || col.name;
        mappedData[col.name] = row[apiKey] !== undefined ? row[apiKey] : row[col.name];
      });
    } else {
      tableColumns.forEach(col => {
        mappedData[col.name] = row[col.name] !== undefined ? row[col.name] : row[col.name.toLowerCase()];
      });
    }
    setFormData(mappedData);
    setCrudModal("edit");
  };

  const openAddModal = () => {
    setSelectedRow(null);
    setFormData({});
    setCrudModal("add");
  };

  // Initial greeting
  useEffect(() => {
    if (messages.length === 0) {
      setMessages([{
        id: "init",
        role: "bot",
        content: "Hello! I am your Medical Supply Assistant.\n\nI have live access to inventory, alerts and forecasts. How can I assist you today?"
      }]);
    }
  }, [messages.length]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isOpen]);

  const handleQuery = async (query: string) => {
    if (!query.trim() || isLoading) return;
    
    const userMsg: Message = { id: Date.now().toString(), role: "user", content: query };
    setMessages((prev) => [...prev, userMsg]);
    setLocalInput("");
    setIsLoading(true);

    const currentMessages = [...messages, userMsg];

    try {
      const response = await fetch("http://127.0.0.1:5001/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages: currentMessages, language: lang }),
      });

      if (!response.ok) throw new Error("Network response was not ok");

      const reader = response.body?.getReader();
      const decoder = new TextDecoder("utf-8");

      let botMsgId = (Date.now() + 1).toString();
      setMessages((prev) => [...prev, { id: botMsgId, role: "bot", content: "" }]);

      if (reader) {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          
          const chunk = decoder.decode(value, { stream: true });
          
          setMessages((prev) => 
            prev.map((msg) => 
              msg.id === botMsgId 
                ? { ...msg, content: msg.content + chunk } 
                : msg
            )
          );
        }
      }
    } catch (error) {
      console.error("Error fetching from backend:", error);
      setMessages((prev) => [...prev, { id: Date.now().toString(), role: "bot", content: "Error connecting to backend database." }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleFormSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    handleQuery(localInput);
  };

  return (
    <>
      {/* Background Page Header */}
      <header className="main-header">
        <div className="header-left">
          <div className="header-text" style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <img src="/logo.png" alt="Logo" style={{ height: '52px', width: '52px', objectFit: 'contain' }} />
            <h1>AI Assistant for Medical Facility</h1>
          </div>
          <nav className="header-nav">
            <button onClick={() => setActiveModal('about')} className="nav-btn">About AI</button>
            <button onClick={() => setActiveModal('how-to-use')} className="nav-btn">How to use</button>
          </nav>
        </div>
        <div className="header-right" style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          {isLoggedIn ? (
            <>
              <span className="officer-badge" style={{ color: '#fff', fontSize: '0.88rem', opacity: 0.9 }}>
                🇮🇳 {officerInfo?.username} ({officerInfo?.sector.toUpperCase()} Command)
              </span>
              <button 
                onClick={() => { setIsLoggedIn(false); setOfficerInfo(null); setActiveTab("overview"); }} 
                className="login-btn"
                style={{ background: '#dc2626', borderColor: '#dc2626', color: '#ffffff', fontWeight: 'bold' }}
              >
                Log Out
              </button>
            </>
          ) : (
            <button onClick={() => setActiveModal('login')} className="login-btn">Login</button>
          )}
        </div>
      </header>

      {/* Main Page Body with Management Dashboard */}
      <main className="p-8" style={{ minHeight: 'calc(100vh - 80px)', background: '#f8fafc', padding: '32px' }}>
        {!isLoggedIn ? null : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', maxWidth: '1400px', margin: '0 auto' }}>
            
            {/* Officer Stats Banner */}
            {activeTab === '' && (
              <div style={{ 
                background: 'linear-gradient(135deg, #cc4433 0%, #e05a47 100%)', 
                padding: '8px 16px', 
                borderRadius: '8px', 
                color: '#fff', 
                boxShadow: '0 2px 4px rgba(0,0,0,0.08)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                fontSize: '0.85rem',
                flexWrap: 'wrap',
                gap: '12px'
              }}>
                <div>
                  <strong>Secured Session Active:</strong> Logged in as <strong>{officerInfo?.username}</strong> | Clearance Level: <strong>Admin Command</strong>
                </div>
                <div style={{ opacity: 0.9 }}>
                  Official Contact: <strong>{officerInfo?.email}</strong>
                </div>
              </div>
            )}

            {/* Horizontal Table Switcher Tabs */}
            {activeTab === '' && (
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px', alignItems: 'center', margin: '16px 0' }}>
                {tables.map((t) => {
                  const colors = getTableColor(t.name);
                  return (
                    <button 
                      key={t.db_name}
                      onClick={() => { setActiveTab(t.name); setActiveTableDbName(t.db_name); }} 
                      style={{
                        display: 'inline-flex', alignItems: 'center', gap: '6px', padding: '6px 14px', borderRadius: '9999px', border: 'none', cursor: 'pointer', fontWeight: 600, fontSize: '0.82rem',
                        background: colors.bg,
                        color: colors.color,
                        transition: 'all 0.2s',
                        textTransform: 'capitalize'
                      }}
                    >
                      {t.name.replace('_', ' ')}
                    </button>
                  );
                })}

                <button 
                  onClick={() => setActiveModal('add-table')}
                  style={{
                    display: 'inline-flex', alignItems: 'center', gap: '6px', padding: '6px 14px', borderRadius: '9999px', border: '1px dashed #10b981', cursor: 'pointer', fontWeight: 600, fontSize: '0.82rem',
                    background: 'transparent',
                    color: '#10b981',
                    transition: 'all 0.2s'
                  }}
                >
                  ➕ Add Table
                </button>
              </div>
            )}

            {/* Tab Display Router */}
            {activeTab === 'overview' || activeTab === '' ? null : (
                <div style={{ background: '#fff', padding: '24px', borderRadius: '12px', border: '1px solid #e2e8f0', boxShadow: '0 1px 3px 0 rgba(0,0,0,0.05)' }}>
                  
                  {/* Table Title and Navigation Header */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginBottom: '24px', borderBottom: '1px solid #f1f5f9', paddingBottom: '16px' }}>
                    <button 
                      onClick={() => { setActiveTab(""); setActiveTableDbName(""); }}
                      style={{
                        display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: '36px', height: '36px', borderRadius: '50%', border: '1px solid #cbd5e1', cursor: 'pointer',
                        background: '#fff',
                        color: '#0f172a',
                        transition: 'all 0.15s',
                        boxShadow: '0 1px 2px 0 rgba(0,0,0,0.05)'
                      }}
                      title="Back to tables"
                    >
                      <ArrowLeft size={18} />
                    </button>
                    <h3 style={{ margin: 0, fontSize: '1.3rem', textTransform: 'capitalize', color: '#0f172a', fontWeight: 700 }}>
                      {activeTab.replace('_', ' ')} Directory
                    </h3>
                  </div>

                  {/* Actions & Filters Top Toolbar */}
                  <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', gap: '16px', marginBottom: '20px' }}>
                    
                    {/* Left Toolbar actions */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                      <button 
                        onClick={handleExportCSV}
                        style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', padding: '8px 16px', borderRadius: '6px', border: '1px solid #cbd5e1', background: '#fff', color: '#475569', fontWeight: 600, fontSize: '0.82rem', cursor: 'pointer', transition: 'all 0.15s' }}
                      >
                        <Download size={14} /> Export
                      </button>

                      <label style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', padding: '8px 16px', borderRadius: '6px', border: '1px solid #cbd5e1', background: '#fff', color: '#475569', fontWeight: 600, fontSize: '0.82rem', cursor: 'pointer', transition: 'all 0.15s' }}>
                        <Upload size={14} /> Import
                        <input type="file" accept=".csv" onChange={handleImportCSV} style={{ display: 'none' }} />
                      </label>

                      <button 
                        disabled={selectedRowIds.length === 0}
                        onClick={handleDeleteSelected}
                        style={{
                          display: 'inline-flex', alignItems: 'center', gap: '6px', padding: '8px 16px', borderRadius: '6px', border: 'none', cursor: selectedRowIds.length === 0 ? 'not-allowed' : 'pointer', fontWeight: 600, fontSize: '0.82rem',
                          background: selectedRowIds.length === 0 ? '#f1f5f9' : '#cc4433',
                          color: selectedRowIds.length === 0 ? '#94a3b8' : '#fff',
                          transition: 'all 0.15s'
                        }}
                      >
                        <Trash2 size={14} /> Delete {selectedRowIds.length > 0 ? `(${selectedRowIds.length})` : ''}
                      </button>
                    </div>

                    {/* Right Toolbar filters */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
                      

                      {/* Search Bar */}
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '6px', padding: '8px 12px', minWidth: '240px' }}>
                        <Search size={14} style={{ color: '#94a3b8' }} />
                        <input 
                          type="text" 
                          value={searchQuery}
                          onChange={(e) => setSearchQuery(e.target.value)}
                          placeholder="Search here..."
                          style={{ border: 'none', background: 'transparent', width: '100%', fontSize: '0.82rem', outline: 'none', color: '#334155' }}
                        />
                      </div>

                      {/* Add new button */}
                      <button 
                        onClick={openAddModal}
                        style={{ background: '#1e3a8a', color: '#fff', border: 'none', padding: '8px 16px', borderRadius: '6px', cursor: 'pointer', fontWeight: 600, fontSize: '0.82rem', display: 'flex', alignItems: 'center', gap: '6px', boxShadow: '0 2px 4px rgba(30, 58, 138, 0.2)', transition: 'all 0.15s' }}
                      >
                        ➕ Add new
                      </button>
                    </div>

                  </div>

                  {/* Responsive Table Scroll Container */}
                  {tableLoading ? (
                    <div style={{ padding: '60px 0', textAlign: 'center', color: '#64748b' }}>
                      <span className="spinner" style={{ display: 'inline-block', width: '24px', height: '24px', border: '3px solid #f3f3f3', borderTop: '3px solid #3b82f6', borderRadius: '50%', animation: 'spin 1s linear infinite', marginBottom: '12px' }}></span>
                      <p style={{ margin: 0 }}>Fetching database rows...</p>
                    </div>
                  ) : tableData.length === 0 ? (
                    <div style={{ padding: '40px 0', textAlign: 'center', color: '#94a3b8' }}>
                      No records found in this table. Click "Add new" to populate.
                    </div>
                  ) : (
                    <div style={{ overflowX: 'auto', maxHeight: '500px', overflowY: 'auto' }}>
                      <table style={{ width: '100%', minWidth: '1200px', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.88rem' }}>
                        <thead>
                          <tr style={{ background: '#fff', borderBottom: '2px solid #e2e8f0' }}>
                            <th style={{ width: '50px', padding: '16px 20px', borderBottom: '2px solid #cbd5e1' }}>
                              <input 
                                type="checkbox"
                                checked={getProcessedData().length > 0 && selectedRowIds.length === getProcessedData().length}
                                onChange={(e) => {
                                  if (e.target.checked) {
                                    setSelectedRowIds(getProcessedData().map(r => r.id));
                                  } else {
                                    setSelectedRowIds([]);
                                  }
                                }}
                                style={{ width: '16px', height: '16px', cursor: 'pointer' }}
                              />
                            </th>
                            <th style={{ padding: '16px 20px', color: '#1e293b', fontWeight: 800, borderBottom: '2px solid #cbd5e1' }}>ID</th>
                            {Object.keys(tableData[0]).filter(k => k !== 'id').map((col) => (
                              <th key={col} style={{ padding: '16px 20px', color: '#1e293b', fontWeight: 800, textTransform: 'capitalize', borderBottom: '2px solid #cbd5e1' }}>
                                {col.replace('_', ' ')}
                              </th>
                            ))}
                            <th style={{ padding: '16px 20px', color: '#1e293b', fontWeight: 800, textAlign: 'center', borderBottom: '2px solid #cbd5e1', width: '80px' }}>Actions</th>
                          </tr>
                        </thead>
                        <tbody>
                          {getProcessedData().map((row, idx) => {
                            const isSelected = selectedRowIds.includes(row.id);
                            return (
                              <tr 
                                key={row.id || idx} 
                                style={{ 
                                  background: isSelected ? '#e6f4ea' : '#ffffff', 
                                  borderBottom: '1px solid #f1f5f9', 
                                  transition: 'background 0.15s' 
                                }}
                              >
                                <td style={{ padding: '16px 20px', borderBottom: '1px solid #f1f5f9' }}>
                                  <input 
                                    type="checkbox"
                                    checked={isSelected}
                                    onChange={(e) => {
                                      if (e.target.checked) {
                                        setSelectedRowIds(prev => [...prev, row.id]);
                                      } else {
                                        setSelectedRowIds(prev => prev.filter(id => id !== row.id));
                                      }
                                    }}
                                    style={{ width: '16px', height: '16px', cursor: 'pointer' }}
                                  />
                                </td>
                                <td style={{ padding: '16px 20px', fontWeight: 700, color: '#0f172a', borderBottom: '1px solid #f1f5f9' }}>{row.id}</td>
                                {Object.entries(row).filter(([k]) => k !== 'id').map(([key, val]) => (
                                  <td key={key} style={{ padding: '16px 20px', color: '#334155', borderBottom: '1px solid #f1f5f9' }}>
                                    {val === null || val === undefined ? '-' : String(val)}
                                  </td>
                                ))}
                                <td style={{ padding: '16px 20px', textAlign: 'center', borderBottom: '1px solid #f1f5f9' }}>
                                  <button 
                                    onClick={() => openEditModal(row)}
                                    style={{ background: 'transparent', color: '#2563eb', border: 'none', padding: '4px', cursor: 'pointer', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', transition: 'all 0.15s' }}
                                    title="Edit Record"
                                  >
                                    <Edit size={16} />
                                  </button>
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              )}
          </div>
        )}
      </main>

      {/* Floating Widget Toggle Button */}
      {!isOpen && !isLoggedIn && (
        <button className="widget-toggle-btn" onClick={() => setIsOpen(true)}>
          <User size={32} />
        </button>
      )}

      {/* Chat Widget Panel */}
      {isOpen && !isLoggedIn && (
        <div className="chat-widget">
          
          {/* Widget Header */}
          <div className="widget-header">
            <div className="widget-header-title" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <img src="/logo.png" alt="Logo" style={{ height: '34px', width: '34px', objectFit: 'contain' }} />
              <div className="widget-header-text">
                <h3>AI Assistant</h3>
                <p>MEDICAL SUPPLY AI</p>
              </div>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <button 
                title="Clear Chat"
                onClick={() => setMessages([])}
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'rgba(255, 255, 255, 0.8)',
                  cursor: 'pointer',
                  padding: '4px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  transition: 'color 0.15s'
                }}
                onMouseEnter={(e) => e.currentTarget.style.color = '#fff'}
                onMouseLeave={(e) => e.currentTarget.style.color = 'rgba(255, 255, 255, 0.8)'}
              >
                <Trash2 size={18} />
              </button>
              <button className="close-btn" onClick={() => setIsOpen(false)}>
                <X size={20} />
              </button>
            </div>
          </div>

          {/* Messages */}
          <div className="chat-messages">
            {messages.map((m) => (
              <div key={m.id} className={`message-wrapper ${m.role}`}>
                <div className="message-label" style={{ color: m.role === 'bot' ? '#b54a39' : '#1a365d' }}>
                  {m.role === 'bot' ? '❖ AAD' : '▶ OPERATOR'}
                </div>
                <div className={`message ${m.role}`}>
                  <div className="markdown-body">
                    <ReactMarkdown 
                      remarkPlugins={[remarkGfm]}
                      components={MemoizedMarkdownComponents}
                    >
                      {m.content}
                    </ReactMarkdown>
                  </div>
                </div>
              </div>
            ))}
            {isLoading && (
              <div className="message-wrapper bot">
                <div className="message-label" style={{ color: '#b54a39' }}>❖ AAD</div>
                <div className="message bot">
                  <div className="flex gap-1 items-center h-4">
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: "0.2s"}}></div>
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: "0.4s"}}></div>
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Quick Actions */}
          <div className="quick-actions">
            <button className="action-pill" onClick={() => handleQuery("Show me low stock alerts")}>
              <AlertTriangle size={14} className="text-orange-500" /> Low Stock
            </button>
            <button className="action-pill" onClick={() => handleQuery("Show medicine inventory")}>
              <Pill size={14} className="text-red-500" /> Medicines
            </button>
            <button className="action-pill" onClick={() => handleQuery("List active contracts")}>
              <FileSignature size={14} className="text-blue-500" /> Contracts
            </button>
            <button className="action-pill" onClick={() => handleQuery("List registered hospitals")}>
              <Building2 size={14} className="text-purple-500" /> Hospitals
            </button>
          </div>

          {/* Input Area */}
          <div className="input-area">
            <form onSubmit={handleFormSubmit} className="input-container">
              <button type="button" className="lang-btn" onClick={() => setLang(lang === 'EN' ? 'HI' : 'EN')}>
                {lang}
              </button>
              <button type="button" className="icon-btn">
                <FileText size={16} />
              </button>
              
              <SpeechToText 
                onTranscript={(text) => setLocalInput(prev => prev ? prev + ' ' + text : text)} 
                className="icon-btn text-red-500"
                language={lang}
              />

              <input
                className="chat-input"
                placeholder="Type your query..."
                value={localInput}
                onChange={(e) => setLocalInput(e.target.value)}
                disabled={isLoading}
              />

              <button type="submit" className="send-btn" disabled={isLoading || !localInput.trim()}>
                <Send size={18} fill="currentColor" />
              </button>
              <button type="button" className="icon-btn text-orange-500">
                <Activity size={18} />
              </button>
            </form>
          </div>
        </div>
      )}

      {/* About AI Modal */}
      {activeModal === 'about' && (
        <div className="modal-overlay" onClick={() => setActiveModal(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header" style={{ background: '#cc4433' }}>
              <h2>About Medical Supply AI</h2>
              <button className="modal-close-btn" onClick={() => setActiveModal(null)}>&times;</button>
            </div>
            <div className="modal-body">
              <p className="mb-4">
                This operations platform bridges frontend visual intelligence with secure military-grade database retrieval. It is designed to assist medical personnel in tracking medicine stocks, suppliers, contracts, and trauma care guidelines.
              </p>
              <h3 className="font-bold mt-4 mb-2 text-[#cc4433]" style={{ fontWeight: 700, marginTop: '16px', marginBottom: '8px' }}>Key Features</h3>
              <ul className="list-disc pl-5 space-y-1">
                <li><strong>Deterministic DVDMS Database</strong>: Directly queries a static SQLite database mirroring official procurement schemas.</li>
                <li><strong>Automatic Data Visualizer</strong>: Renders responsive charts (Pie, Line, Bar) dynamically based on user requests.</li>
                <li><strong>Trauma Protocols Retriever</strong>: Built-in semantic search for critical field medical guides (TCCC/ATLS).</li>
                <li><strong>Dynamic Context Memory</strong>: Dual-language translation memory isolated to prevent mixing scripts.</li>
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* How To Use Modal */}
      {activeModal === 'how-to-use' && (
        <div className="modal-overlay" onClick={() => setActiveModal(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header" style={{ background: '#cc4433' }}>
              <h2>How to Use the Assistant</h2>
              <button className="modal-close-btn" onClick={() => setActiveModal(null)}>&times;</button>
            </div>
            <div className="modal-body">
              <ol className="list-decimal pl-5 space-y-3" style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                <li>
                  <strong>Query Database Views</strong>: Ask the chat widget directly about inventory, alerts, or suppliers. E.g., <em>"Show medicine inventory"</em> or <em>"Show low stock alerts"</em>.
                </li>
                <li>
                  <strong>Generate Visual Charts</strong>: Include keywords like <em>"graph"</em>, <em>"chart"</em>, <em>"visualize"</em>, or <em>"pie"</em> to render charts automatically (e.g., <em>"graph for paracetamol quantity"</em>).
                </li>
                <li>
                  <strong>Interactive Chart Expansion</strong>: Click <strong>⛶ Expand</strong> on any chart panel to expand it into a full-sized scrollable view to prevent text overlays.
                </li>
                <li>
                  <strong>Switch Language</strong>: Click the language indicator (EN/HI) next to the text input box to translate responses and inventory tables instantly.
                </li>
                <li>
                  <strong>Voice Transcription</strong>: Use the Microphone button to transcribe voice queries directly into the chat input.
                </li>
              </ol>
            </div>
          </div>
        </div>
      )}

      {/* Secured Login / Signup Modal */}
      {activeModal === 'login' && (
        <div className="modal-overlay" onClick={() => setActiveModal(null)}>
          <div 
            className="modal-content" 
            onClick={(e) => e.stopPropagation()} 
            style={{ 
              maxWidth: '420px', 
              maxHeight: '95vh',
              overflowY: 'auto',
              borderRadius: '20px', 
              boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
              background: '#fff',
              border: 'none',
              position: 'relative',
              padding: '24px 28px'
            }}
          >
            {/* Absolute Close Button */}
            <button 
              onClick={() => setActiveModal(null)} 
              style={{
                position: 'absolute',
                top: '16px',
                right: '16px',
                background: 'none',
                border: 'none',
                color: '#94a3b8',
                cursor: 'pointer',
                fontSize: '1.25rem',
                transition: 'color 0.15s'
              }}
              onMouseEnter={(e) => e.currentTarget.style.color = '#334155'}
              onMouseLeave={(e) => e.currentTarget.style.color = '#94a3b8'}
            >
              <X size={20} />
            </button>

            {/* Top Icon Branding */}
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', marginBottom: '20px', textAlign: 'center' }}>
              <div style={{
                width: '48px',
                height: '48px',
                borderRadius: '50%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                marginBottom: '10px',
                overflow: 'hidden'
              }}>
                <img src="/logo.png" alt="Logo" style={{ width: '100%', height: '100%', objectFit: 'contain' }} />
              </div>
              <h2 style={{ fontSize: '1.35rem', fontWeight: 700, color: '#0f172a', margin: '0' }}>
                {loginView === 'login' ? 'Welcome Back' : 'Create Account'}
              </h2>
            </div>

            {loginView === 'login' ? (
              /* Login View */
              <form onSubmit={handleLoginSubmit}>
                <div className="form-group" style={{ marginBottom: '12px' }}>
                  <label htmlFor="login-username" style={{ fontSize: '0.8rem', fontWeight: 600, color: '#475569', marginBottom: '4px' }}>Username</label>
                  <input 
                    type="text" 
                    id="login-username" 
                    className="form-input" 
                    placeholder="Enter username..." 
                    value={loginUsername}
                    onChange={(e) => setLoginUsername(e.target.value)}
                    required 
                    style={{
                      borderRadius: '8px',
                      background: '#f8fafc',
                      border: '1px solid #e2e8f0',
                      padding: '8px 12px',
                      fontSize: '0.88rem'
                    }}
                  />
                </div>
                <div className="form-group" style={{ marginBottom: '14px' }}>
                  <label htmlFor="login-password" style={{ fontSize: '0.8rem', fontWeight: 600, color: '#475569', marginBottom: '4px' }}>Password</label>
                  <input 
                    type="password" 
                    id="login-password" 
                    className="form-input" 
                    placeholder="Enter password..." 
                    value={loginPassword}
                    onChange={(e) => setLoginPassword(e.target.value)}
                    required 
                    style={{
                      borderRadius: '8px',
                      background: '#f8fafc',
                      border: '1px solid #e2e8f0',
                      padding: '8px 12px',
                      fontSize: '0.88rem'
                    }}
                  />
                </div>

                {/* Inline CAPTCHA Display */}
                <div className="form-group" style={{ marginBottom: '20px' }}>
                  <label htmlFor="captcha-login" style={{ fontSize: '0.8rem', fontWeight: 600, color: '#475569', marginBottom: '4px' }}>Security Verification (CAPTCHA)</label>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <div style={{
                      background: '#f1f5f9',
                      padding: '6px 12px',
                      borderRadius: '6px',
                      fontFamily: 'monospace',
                      fontWeight: 'bold',
                      fontSize: '1.05rem',
                      letterSpacing: '2px',
                      fontStyle: 'italic',
                      textDecoration: 'line-through',
                      color: '#475569',
                      userSelect: 'none',
                      border: '1px dashed #cbd5e1'
                    }}>
                      {captchaCode}
                    </div>
                    <input 
                      type="text" 
                      id="captcha-login" 
                      className="form-input" 
                      placeholder="Enter CAPTCHA..." 
                      value={captchaInput}
                      onChange={(e) => setCaptchaInput(e.target.value)}
                      required 
                      style={{
                        flex: 1,
                        borderRadius: '8px',
                        background: '#f8fafc',
                        border: '1px solid #e2e8f0',
                        padding: '8px 12px',
                        fontSize: '0.88rem'
                      }}
                    />
                    <button type="button" onClick={generateCaptcha} style={{
                      background: 'none',
                      border: 'none',
                      color: '#cc4433',
                      cursor: 'pointer',
                      fontSize: '0.8rem',
                      textDecoration: 'underline',
                      fontWeight: 600,
                      whiteSpace: 'nowrap'
                    }}>
                      Refresh
                    </button>
                  </div>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginTop: '20px' }}>
                  <button 
                    type="submit" 
                    style={{ 
                      width: '100%', 
                      background: '#cc4433', 
                      color: '#fff', 
                      border: 'none', 
                      padding: '10px 24px', 
                      borderRadius: '9999px', 
                      fontWeight: 600, 
                      fontSize: '0.92rem',
                      cursor: 'pointer', 
                      transition: 'all 0.15s',
                      boxShadow: '0 4px 6px -1px rgba(204, 68, 51, 0.2)'
                    }}
                    onMouseEnter={(e) => e.currentTarget.style.opacity = '0.9'}
                    onMouseLeave={(e) => e.currentTarget.style.opacity = '1'}
                  >
                    Sign In
                  </button>
                  <div style={{ textAlign: 'center', fontSize: '0.82rem' }}>
                    <span style={{ color: '#64748b' }}>Don't have an account? </span>
                    <button 
                      type="button" 
                      onClick={() => { setLoginView('signup'); generateCaptcha(); }}
                      style={{ color: '#cc4433', fontWeight: 600, background: 'none', border: 'none', cursor: 'pointer', padding: 0, textDecoration: 'underline' }}
                    >
                      Register here
                    </button>
                  </div>
                </div>
              </form>
            ) : (
              /* Signup View */
              <form onSubmit={handleSignupSubmit}>
                <div className="form-group" style={{ marginBottom: '10px' }}>
                  <label htmlFor="signup-email" style={{ fontSize: '0.8rem', fontWeight: 600, color: '#475569', marginBottom: '4px' }}>Official Gmail / Email</label>
                  <input 
                    type="email" 
                    id="signup-email" 
                    className="form-input" 
                    placeholder="Enter official email..." 
                    value={signupEmail}
                    onChange={(e) => setSignupEmail(e.target.value)}
                    required 
                    style={{
                      borderRadius: '8px',
                      background: '#f8fafc',
                      border: '1px solid #e2e8f0',
                      padding: '8px 12px',
                      fontSize: '0.88rem'
                    }}
                  />
                </div>
                <div className="form-group" style={{ marginBottom: '10px' }}>
                  <label htmlFor="signup-username" style={{ fontSize: '0.8rem', fontWeight: 600, color: '#475569', marginBottom: '4px' }}>Username</label>
                  <input 
                    type="text" 
                    id="signup-username" 
                    className="form-input" 
                    placeholder="Choose username..." 
                    value={signupUsername}
                    onChange={(e) => setSignupUsername(e.target.value)}
                    required 
                    style={{
                      borderRadius: '8px',
                      background: '#f8fafc',
                      border: '1px solid #e2e8f0',
                      padding: '8px 12px',
                      fontSize: '0.88rem'
                    }}
                  />
                </div>
                <div className="form-group" style={{ marginBottom: '12px' }}>
                  <label htmlFor="signup-password" style={{ fontSize: '0.8rem', fontWeight: 600, color: '#475569', marginBottom: '4px' }}>Password</label>
                  <input 
                    type="password" 
                    id="signup-password" 
                    className="form-input" 
                    placeholder="Enter strong password..." 
                    value={signupPassword}
                    onChange={(e) => setSignupPassword(e.target.value)}
                    required 
                    style={{
                      borderRadius: '8px',
                      background: '#f8fafc',
                      border: '1px solid #e2e8f0',
                      padding: '8px 12px',
                      fontSize: '0.88rem',
                      marginBottom: '6px'
                    }}
                  />
                  {/* Password criteria display - 2x2 Grid */}
                  <div style={{ fontSize: '0.72rem', padding: '8px', background: '#f8fafc', borderRadius: '8px', border: '1px solid #e2e8f0', color: '#475569' }}>
                    <p style={{ fontWeight: 600, margin: '0 0 4px 0' }}>Password Strength:</p>
                    <ul style={{ listStyleType: 'none', paddingLeft: 0, margin: 0, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '3px' }}>
                      <li style={{ color: signupPassword.length >= 8 ? '#16a34a' : '#dc2626', display: 'flex', alignItems: 'center', gap: '4px', fontWeight: 500 }}>
                        <span>{signupPassword.length >= 8 ? '✓' : '✗'}</span> 8+ chars
                      </li>
                      <li style={{ color: /[A-Z]/.test(signupPassword) ? '#16a34a' : '#dc2626', display: 'flex', alignItems: 'center', gap: '4px', fontWeight: 500 }}>
                        <span>{/[A-Z]/.test(signupPassword) ? '✓' : '✗'}</span> Uppercase
                      </li>
                      <li style={{ color: /[0-9]/.test(signupPassword) ? '#16a34a' : '#dc2626', display: 'flex', alignItems: 'center', gap: '4px', fontWeight: 500 }}>
                        <span>{/[0-9]/.test(signupPassword) ? '✓' : '✗'}</span> Number
                      </li>
                      <li style={{ color: /[^A-Za-z0-9]/.test(signupPassword) ? '#16a34a' : '#dc2626', display: 'flex', alignItems: 'center', gap: '4px', fontWeight: 500 }}>
                        <span>{/[^A-Za-z0-9]/.test(signupPassword) ? '✓' : '✗'}</span> Special char
                      </li>
                    </ul>
                  </div>
                </div>

                {/* Inline CAPTCHA Display */}
                <div className="form-group" style={{ marginBottom: '20px' }}>
                  <label htmlFor="captcha-signup" style={{ fontSize: '0.8rem', fontWeight: 600, color: '#475569', marginBottom: '4px' }}>Security Verification (CAPTCHA)</label>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <div style={{
                      background: '#f1f5f9',
                      padding: '6px 12px',
                      borderRadius: '6px',
                      fontFamily: 'monospace',
                      fontWeight: 'bold',
                      fontSize: '1.05rem',
                      letterSpacing: '2px',
                      fontStyle: 'italic',
                      textDecoration: 'line-through',
                      color: '#475569',
                      userSelect: 'none',
                      border: '1px dashed #cbd5e1'
                    }}>
                      {captchaCode}
                    </div>
                    <input 
                      type="text" 
                      id="captcha-signup" 
                      className="form-input" 
                      placeholder="Enter CAPTCHA..." 
                      value={captchaInput}
                      onChange={(e) => setCaptchaInput(e.target.value)}
                      required 
                      style={{
                        flex: 1,
                        borderRadius: '8px',
                        background: '#f8fafc',
                        border: '1px solid #e2e8f0',
                        padding: '8px 12px',
                        fontSize: '0.88rem'
                      }}
                    />
                    <button type="button" onClick={generateCaptcha} style={{
                      background: 'none',
                      border: 'none',
                      color: '#cc4433',
                      cursor: 'pointer',
                      fontSize: '0.8rem',
                      textDecoration: 'underline',
                      fontWeight: 600,
                      whiteSpace: 'nowrap'
                    }}>
                      Refresh
                    </button>
                  </div>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginTop: '20px' }}>
                  <button 
                    type="submit" 
                    style={{ 
                      width: '100%', 
                      background: '#cc4433', 
                      color: '#fff', 
                      border: 'none', 
                      padding: '10px 24px', 
                      borderRadius: '9999px', 
                      fontWeight: 600, 
                      fontSize: '0.92rem',
                      cursor: 'pointer', 
                      transition: 'all 0.15s',
                      boxShadow: '0 4px 6px -1px rgba(204, 68, 51, 0.2)'
                    }}
                    onMouseEnter={(e) => e.currentTarget.style.opacity = '0.9'}
                    onMouseLeave={(e) => e.currentTarget.style.opacity = '1'}
                  >
                    Sign Up
                  </button>
                  <div style={{ textAlign: 'center', fontSize: '0.82rem' }}>
                    <span style={{ color: '#64748b' }}>Already registered? </span>
                    <button 
                      type="button" 
                      onClick={() => { setLoginView('login'); generateCaptcha(); }}
                      style={{ color: '#cc4433', fontWeight: 600, background: 'none', border: 'none', cursor: 'pointer', padding: 0, textDecoration: 'underline' }}
                    >
                      Login here
                    </button>
                  </div>
                </div>
              </form>
            )}
          </div>
        </div>
      )}

      {/* Add Table Modal */}
      {activeModal === 'add-table' && (
        <div className="modal-overlay" onClick={() => setActiveModal(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '450px' }}>
            <div className="modal-header">
              <h2>Add New Database Table</h2>
              <button className="modal-close-btn" onClick={() => setActiveModal(null)}>&times;</button>
            </div>
            <div className="modal-body">
              <form onSubmit={handleCreateTable}>
                <div className="form-group">
                  <label htmlFor="new-table-name">Table Name</label>
                  <input 
                    type="text" 
                    id="new-table-name" 
                    className="form-input" 
                    placeholder="e.g. equipment, personnel..." 
                    value={newTableName}
                    onChange={(e) => setNewTableName(e.target.value)}
                    required 
                  />
                  <p style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '6px' }}>
                    Note: A secure dynamic table will be generated in SQLite containing standard fields: <strong>id</strong>, <strong>name</strong>, <strong>description</strong>, and <strong>status</strong>.
                  </p>
                </div>
                <div className="form-actions">
                  <button type="button" className="form-cancel-btn" onClick={() => setActiveModal(null)}>Cancel</button>
                  <button type="submit" className="form-submit-btn" style={{ background: '#10b981', borderColor: '#10b981' }}>Create Table</button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}

      {/* CRUD Add / Edit Modal */}
      {crudModal && (
        <div className="modal-overlay" onClick={() => setCrudModal(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '600px' }}>
            <div className="modal-header">
              <h2>{crudModal === 'add' ? `Add New Record (${activeTab.replace('_', ' ')})` : `Edit Record ID: ${selectedRow?.id} (${activeTab.replace('_', ' ')})`}</h2>
              <button className="modal-close-btn" onClick={() => setCrudModal(null)}>&times;</button>
            </div>
            <div className="modal-body" style={{ maxHeight: '70vh', overflowY: 'auto', paddingRight: '8px' }}>
              <form onSubmit={handleCrudSubmit}>
                {/* Dynamically render form inputs based on table tab */}
                
                {tableColumns.map((col) => {
                  const lowerName = col.name.toLowerCase();
                  const isIdOrMetadataField = 
                    lowerName === 'id' || 
                    lowerName.includes('id') || 
                    lowerName.includes('code') || 
                    lowerName.includes('type') || 
                    lowerName.includes('make') || 
                    lowerName.includes('unit') || 
                    lowerName.includes('remarks');
                    
                  if (isIdOrMetadataField) return null;
                  
                  let inputType = "text";
                  const lowerType = col.type.toLowerCase();
                  if (lowerType.includes("int") || lowerType.includes("real") || lowerType.includes("float") || lowerType.includes("numeric") || lowerType.includes("double")) {
                    inputType = "number";
                  } else if (lowerType.includes("date")) {
                    inputType = "date";
                  }
                  
                  return (
                    <div className="form-group" key={col.name}>
                      <label style={{ textTransform: 'capitalize' }}>
                        {col.name.replace(/^[gh]st(str|num|dt)?/, '').replace('_', ' ')}
                      </label>
                      {col.name.toLowerCase().includes("remarks") || col.name.toLowerCase().includes("specification") || col.name.toLowerCase().includes("address") ? (
                        <textarea
                          className="form-input"
                          value={formData[col.name] ?? ''}
                          onChange={(e) => setFormData({ ...formData, [col.name]: e.target.value })}
                          disabled={isIdOrMetadataField && crudModal === 'edit'}
                          required={col.name === 'name' || col.name === 'id'}
                        />
                      ) : col.name === 'ved_category' ? (
                        <select
                          className="form-input"
                          value={formData[col.name] ?? 'E'}
                          onChange={(e) => setFormData({ ...formData, [col.name]: e.target.value })}
                          required
                        >
                          <option value="V">V (Vital)</option>
                          <option value="E">E (Essential)</option>
                          <option value="D">D (Desirable)</option>
                        </select>
                      ) : (
                        <input
                          type={inputType}
                          className="form-input"
                          value={formData[col.name] ?? ''}
                          onChange={(e) => {
                            const val = inputType === 'number' ? parseFloat(e.target.value) : e.target.value;
                            setFormData({ ...formData, [col.name]: val });
                          }}
                          disabled={isIdOrMetadataField && crudModal === 'edit'}
                          required={col.name === 'name' || col.name === 'id'}
                        />
                      )}
                    </div>
                  );
                })}

                <div className="form-actions" style={{ marginTop: '20px' }}>
                  <button type="button" className="form-cancel-btn" onClick={() => setCrudModal(null)}>Cancel</button>
                  <button type="submit" className="form-submit-btn" style={{ background: '#10b981', borderColor: '#10b981' }}>Save Changes</button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
