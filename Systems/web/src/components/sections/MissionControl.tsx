import { useEffect, useState, useRef } from 'react';
import { useI18n } from '../../contexts/I18nContext';
import { api } from '../../api';
import { Activity, Server, Database, Zap, Users, MessageSquare, AlertTriangle, TrendingUp, Cpu, HardDrive, Wifi } from 'lucide-react';
import { LineChart, Line, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';

type Metric = {
  time: string;
  rps: number;
  responseTime: number;
  errorRate: number;
};

type SystemMetrics = {
  cpu: number;
  ram: number;
  ramUsed: number;
  ramTotal: number;
  disk: number;
  diskUsed: number;
  diskTotal: number;
  redis: number;
  redisUsed: number;
  redisTotal: number;
  dbConnections: number;
  activeUsers: number;
  newUsersToday: number;
  queueSize: number;
};

const COLORS = ['#6366f1', '#8b5cf6', '#ec4899', '#f59e0b', '#10b981'];

// Format bytes to human readable format
const formatBytes = (bytes: number): string => {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`;
};

export const MissionControl = () => {
  const { t } = useI18n();
  const [metrics, setMetrics] = useState<Metric[]>([]);
  const [systemMetrics, setSystemMetrics] = useState<SystemMetrics>({
    cpu: 0,
    ram: 0,
    ramUsed: 0,
    ramTotal: 0,
    disk: 0,
    diskUsed: 0,
    diskTotal: 0,
    redis: 0,
    redisUsed: 0,
    redisTotal: 0,
    dbConnections: 0,
    activeUsers: 0,
    newUsersToday: 0,
    queueSize: 0,
  });
  const [errorRate, setErrorRate] = useState<'low' | 'medium' | 'high'>('low');
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const loadMetrics = async () => {
      try {
        // Load system metrics
        const sysMetrics = await api.getSystemMetrics();
        setSystemMetrics({
          cpu: sysMetrics.cpu,
          ram: sysMetrics.ram,
          ramUsed: sysMetrics.ramUsed || 0,
          ramTotal: sysMetrics.ramTotal || 0,
          disk: sysMetrics.disk,
          diskUsed: sysMetrics.diskUsed || 0,
          diskTotal: sysMetrics.diskTotal || 0,
          redis: sysMetrics.redis,
          redisUsed: sysMetrics.redisUsed || 0,
          redisTotal: sysMetrics.redisTotal || 0,
          dbConnections: sysMetrics.dbConnections,
          activeUsers: 0, // Will be updated from live metrics
          newUsersToday: 0, // Will be updated from live metrics
          queueSize: 0, // Will be updated from live metrics
        });

        // Load live metrics
        const liveMetrics = await api.getLiveMetrics();
        const now = new Date().toLocaleTimeString();
        const newMetric: Metric = {
          time: now,
          rps: liveMetrics.rps,
          responseTime: liveMetrics.responseTime,
          errorRate: liveMetrics.errorRate,
        };

        setMetrics((prev) => {
          const updated = [...prev, newMetric];
          return updated.slice(-20); // Keep last 20 points
        });

        // Update error rate status
        if (liveMetrics.errorRate > 3) {
          setErrorRate('high');
        } else if (liveMetrics.errorRate > 1) {
          setErrorRate('medium');
        } else {
          setErrorRate('low');
        }

        // Update system metrics with live data
        setSystemMetrics((prev) => ({
          ...prev,
          activeUsers: liveMetrics.activeUsers,
          newUsersToday: liveMetrics.newUsersToday,
          queueSize: liveMetrics.queueSize,
        }));
      } catch (error) {
        console.error('Error loading metrics:', error);
      }
    };

    // Load immediately
    loadMetrics();

    // Then update every 2-5 seconds
    const interval = setInterval(loadMetrics, 3000);

    return () => {
      clearInterval(interval);
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  const pieData = [
    { name: 'Used', value: systemMetrics.cpu },
    { name: 'Free', value: 100 - systemMetrics.cpu },
  ];

  const ramData = [
    { name: 'Used', value: systemMetrics.ram },
    { name: 'Free', value: 100 - systemMetrics.ram },
  ];

  const diskData = [
    { name: 'Used', value: systemMetrics.disk },
    { name: 'Free', value: 100 - systemMetrics.disk },
  ];

  return (
    <div>
      {/* Page Header */}
      <div className="mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold mb-2" style={{ color: 'var(--oneui-text)' }}>
              🛰️ Mission Control
            </h1>
            <p className="oneui-text-muted">Real-time system monitoring and control center</p>
          </div>
          <div className={`px-4 py-2 rounded-lg flex items-center gap-2 ${
            errorRate === 'low' ? 'bg-green-500/20 text-green-500' :
            errorRate === 'medium' ? 'bg-yellow-500/20 text-yellow-500' :
            'bg-red-500/20 text-red-500'
          }`}>
            <div className={`w-2 h-2 rounded-full ${
              errorRate === 'low' ? 'bg-green-500' :
              errorRate === 'medium' ? 'bg-yellow-500' :
              'bg-red-500'
            } animate-pulse`} />
            <span className="font-semibold">
              {errorRate === 'low' ? 'All Systems Operational' :
               errorRate === 'medium' ? 'Minor Issues Detected' :
               'Critical Issues'}
            </span>
          </div>
        </div>
      </div>

      {/* Live Metrics Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        {/* RPS Chart */}
        <div className="oneui-card">
          <div className="oneui-card-header">
            <div className="flex items-center gap-2">
              <Activity className="w-5 h-5" style={{ color: 'var(--oneui-primary)' }} />
              <h3 className="oneui-card-title">Requests Per Second</h3>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={200}>
            <AreaChart data={metrics}>
              <defs>
                <linearGradient id="colorRps" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#6366f1" stopOpacity={0.8}/>
                  <stop offset="95%" stopColor="#6366f1" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
              <XAxis dataKey="time" stroke="var(--oneui-text-muted)" fontSize={12} />
              <YAxis stroke="var(--oneui-text-muted)" fontSize={12} />
              <Tooltip contentStyle={{ backgroundColor: 'var(--oneui-bg)', border: '1px solid var(--oneui-border)' }} />
              <Area type="monotone" dataKey="rps" stroke="#6366f1" fillOpacity={1} fill="url(#colorRps)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Response Time Chart */}
        <div className="oneui-card">
          <div className="oneui-card-header">
            <div className="flex items-center gap-2">
              <Zap className="w-5 h-5" style={{ color: 'var(--oneui-warning)' }} />
              <h3 className="oneui-card-title">Response Time (ms)</h3>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={metrics}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
              <XAxis dataKey="time" stroke="var(--oneui-text-muted)" fontSize={12} />
              <YAxis stroke="var(--oneui-text-muted)" fontSize={12} />
              <Tooltip contentStyle={{ backgroundColor: 'var(--oneui-bg)', border: '1px solid var(--oneui-border)' }} />
              <Line type="monotone" dataKey="responseTime" stroke="#f59e0b" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Infrastructure Status */}
      <div className="mb-6">
        <h2 className="text-lg font-semibold mb-4" style={{ color: 'var(--oneui-text)' }}>
          Infrastructure Status
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {/* CPU */}
          <div className="oneui-card">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <Cpu className="w-5 h-5" style={{ color: 'var(--oneui-primary)' }} />
                <span className="font-medium" style={{ color: 'var(--oneui-text)' }}>CPU</span>
              </div>
              <span className="text-lg font-bold" style={{ color: 'var(--oneui-text)' }}>
                {systemMetrics.cpu.toFixed(1)}%
              </span>
            </div>
            <div className="text-xs oneui-text-muted mb-3 text-center">
              {systemMetrics.cpu.toFixed(1)}% used
            </div>
            <ResponsiveContainer width="100%" height={100}>
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="50%"
                  innerRadius={25}
                  outerRadius={40}
                  startAngle={90}
                  endAngle={-270}
                  dataKey="value"
                >
                  {pieData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={index === 0 ? '#6366f1' : 'rgba(255,255,255,0.1)'} />
                  ))}
                </Pie>
              </PieChart>
            </ResponsiveContainer>
          </div>

          {/* RAM */}
          <div className="oneui-card">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <Server className="w-5 h-5" style={{ color: 'var(--oneui-success)' }} />
                <span className="font-medium" style={{ color: 'var(--oneui-text)' }}>RAM</span>
              </div>
              <span className="text-lg font-bold" style={{ color: 'var(--oneui-text)' }}>
                {systemMetrics.ram.toFixed(1)}%
              </span>
            </div>
            <div className="text-xs oneui-text-muted mb-3 text-center">
              {systemMetrics.ramTotal > 0 ? (
                <>
                  {formatBytes(systemMetrics.ramUsed)} / {formatBytes(systemMetrics.ramTotal)}
                </>
              ) : (
                'N/A'
              )}
            </div>
            <ResponsiveContainer width="100%" height={100}>
              <PieChart>
                <Pie
                  data={ramData}
                  cx="50%"
                  cy="50%"
                  innerRadius={25}
                  outerRadius={40}
                  startAngle={90}
                  endAngle={-270}
                  dataKey="value"
                >
                  {ramData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={index === 0 ? '#10b981' : 'rgba(255,255,255,0.1)'} />
                  ))}
                </Pie>
              </PieChart>
            </ResponsiveContainer>
          </div>

          {/* Disk */}
          <div className="oneui-card">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <HardDrive className="w-5 h-5" style={{ color: 'var(--oneui-warning)' }} />
                <span className="font-medium" style={{ color: 'var(--oneui-text)' }}>Disk</span>
              </div>
              <span className="text-lg font-bold" style={{ color: 'var(--oneui-text)' }}>
                {systemMetrics.disk.toFixed(1)}%
              </span>
            </div>
            <div className="text-xs oneui-text-muted mb-3 text-center">
              {systemMetrics.diskTotal > 0 ? (
                <>
                  {formatBytes(systemMetrics.diskUsed)} / {formatBytes(systemMetrics.diskTotal)}
                </>
              ) : (
                'N/A'
              )}
            </div>
            <ResponsiveContainer width="100%" height={100}>
              <PieChart>
                <Pie
                  data={diskData}
                  cx="50%"
                  cy="50%"
                  innerRadius={25}
                  outerRadius={40}
                  startAngle={90}
                  endAngle={-270}
                  dataKey="value"
                >
                  {diskData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={index === 0 ? '#f59e0b' : 'rgba(255,255,255,0.1)'} />
                  ))}
                </Pie>
              </PieChart>
            </ResponsiveContainer>
          </div>

          {/* Redis */}
          <div className="oneui-card">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <Database className="w-5 h-5" style={{ color: 'var(--oneui-danger)' }} />
                <span className="font-medium" style={{ color: 'var(--oneui-text)' }}>Redis</span>
              </div>
              <span className="text-lg font-bold" style={{ color: 'var(--oneui-text)' }}>
                {systemMetrics.redis.toFixed(1)}%
              </span>
            </div>
            <div className="text-xs oneui-text-muted mb-3 text-center">
              {systemMetrics.redisTotal > 0 ? (
                <>
                  {formatBytes(systemMetrics.redisUsed)} / {formatBytes(systemMetrics.redisTotal)}
                </>
              ) : (
                'N/A'
              )}
            </div>
            <div className="mt-2">
              <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                <div
                  className="bg-red-500 h-2 rounded-full transition-all"
                  style={{ width: `${systemMetrics.redis}%` }}
                />
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Business Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="oneui-card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm oneui-text-muted mb-1">Active Users (24h)</p>
              <p className="text-2xl font-bold" style={{ color: 'var(--oneui-text)' }}>
                {systemMetrics.activeUsers.toLocaleString()}
              </p>
            </div>
            <Users className="w-8 h-8" style={{ color: 'var(--oneui-primary)' }} />
          </div>
        </div>

        <div className="oneui-card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm oneui-text-muted mb-1">New Users Today</p>
              <p className="text-2xl font-bold" style={{ color: 'var(--oneui-text)' }}>
                {systemMetrics.newUsersToday}
              </p>
            </div>
            <TrendingUp className="w-8 h-8" style={{ color: 'var(--oneui-success)' }} />
          </div>
        </div>

        <div className="oneui-card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm oneui-text-muted mb-1">Queue Size</p>
              <p className="text-2xl font-bold" style={{ color: 'var(--oneui-text)' }}>
                {systemMetrics.queueSize}
              </p>
            </div>
            <MessageSquare className="w-8 h-8" style={{ color: 'var(--oneui-warning)' }} />
          </div>
        </div>

        <div className="oneui-card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm oneui-text-muted mb-1">DB Connections</p>
              <p className="text-2xl font-bold" style={{ color: 'var(--oneui-text)' }}>
                {systemMetrics.dbConnections}
              </p>
            </div>
            <Wifi className="w-8 h-8" style={{ color: 'var(--oneui-info)' }} />
          </div>
        </div>
      </div>
    </div>
  );
};

