import React, { CSSProperties, InputHTMLAttributes, PropsWithChildren, useEffect, useMemo, useState } from 'react';
import {
  BarChart as ReBarChart,
  Bar,
  CartesianGrid,
  LineChart as ReLineChart,
  Line,
  PieChart as RePieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  Legend,
} from 'recharts';

const toneColors: Record<string, string> = {
  info: '#2563eb',
  success: '#16a34a',
  warning: '#f97316',
  danger: '#dc2626',
  neutral: '#64748b',
};

const canvasStateStore = new Map<string, unknown>();
const canvasStateListeners = new Map<string, Set<(value: unknown) => void>>();

function readStoredCanvasState<T>(storageKey: string, initial: T): T {
  if (canvasStateStore.has(storageKey)) {
    return canvasStateStore.get(storageKey) as T;
  }

  if (typeof window === 'undefined') {
    canvasStateStore.set(storageKey, initial);
    return initial;
  }

  const stored = window.localStorage.getItem(storageKey);
  if (!stored) {
    canvasStateStore.set(storageKey, initial);
    return initial;
  }

  try {
    const parsed = JSON.parse(stored) as T;
    canvasStateStore.set(storageKey, parsed);
    return parsed;
  } catch {
    canvasStateStore.set(storageKey, initial);
    return initial;
  }
}

export function useCanvasState<T>(key: string, initial: T): [T, (value: T) => void] {
  const pathKey = typeof window === 'undefined' ? 'server' : window.location.pathname;
  const storageKey = `canvas:${pathKey}:${key}`;
  const [state, setState] = useState<T>(() => readStoredCanvasState(storageKey, initial));

  useEffect(() => {
    const listener = (value: unknown) => setState(value as T);
    const listeners = canvasStateListeners.get(storageKey) ?? new Set<(value: unknown) => void>();
    listeners.add(listener);
    canvasStateListeners.set(storageKey, listeners);

    return () => {
      listeners.delete(listener);
      if (listeners.size === 0) {
        canvasStateListeners.delete(storageKey);
      }
    };
  }, [storageKey]);

  const update = (value: T) => {
    canvasStateStore.set(storageKey, value);
    setState(value);
    if (typeof window !== 'undefined') {
      window.localStorage.setItem(storageKey, JSON.stringify(value));
    }
    canvasStateListeners.get(storageKey)?.forEach((listener) => listener(value));
  };

  return [state, update];
}

export function Stack({ gap = 12, children }: PropsWithChildren<{ gap?: number }>) {
  return (
    <div className="stack" style={{ gap }}>
      {children}
    </div>
  );
}

export function Row({ gap = 8, wrap = false, children }: PropsWithChildren<{ gap?: number; wrap?: boolean }>) {
  return (
    <div className="row" style={{ gap, flexWrap: wrap ? 'wrap' : 'nowrap' }}>
      {children}
    </div>
  );
}

export function Grid({ columns = 2, gap = 12, children }: PropsWithChildren<{ columns?: number; gap?: number }>) {
  return (
    <div className="grid" style={{ gridTemplateColumns: `repeat(${columns}, minmax(0, 1fr))`, gap }}>
      {children}
    </div>
  );
}

export function Card({ children }: PropsWithChildren) {
  return <div className="card">{children}</div>;
}

export function CardHeader({ children }: PropsWithChildren) {
  return <div className="card-header">{children}</div>;
}

export function CardBody({ children }: PropsWithChildren) {
  return <div className="card-body">{children}</div>;
}

export function Callout({ title, tone = 'info', children }: PropsWithChildren<{ title?: string; tone?: string }>) {
  return (
    <div className={`callout ${tone}`}>
      {title ? <strong style={{ display: 'block', marginBottom: 6 }}>{title}</strong> : null}
      {children}
    </div>
  );
}

export function H1({ children }: PropsWithChildren) {
  return <h1 style={{ margin: 0, fontSize: 28 }}>{children}</h1>;
}

export function H2({ children }: PropsWithChildren) {
  return <h2 style={{ margin: 0, fontSize: 22 }}>{children}</h2>;
}

export function H3({ children }: PropsWithChildren) {
  return <h3 style={{ margin: 0, fontSize: 18 }}>{children}</h3>;
}

export function Text({ children, tone, size }: PropsWithChildren<{ tone?: string; size?: 'small' | 'normal' }>) {
  const color = tone === 'secondary' ? '#64748b' : '#0f172a';
  const fontSize = size === 'small' ? 12 : 14;
  return (
    <p style={{ margin: 0, color, fontSize, lineHeight: 1.6 }}>
      {children}
    </p>
  );
}

export function Code({ children }: PropsWithChildren) {
  return <code className="code">{children}</code>;
}

export function Divider() {
  return <div className="divider" />;
}

export function Pill({ children, active = false, onClick }: PropsWithChildren<{ active?: boolean; onClick?: () => void }>) {
  return (
    <button type="button" className={`pill ${active ? 'active' : ''}`} onClick={onClick} aria-pressed={active}>
      {children}
    </button>
  );
}

export function Button({ children, variant = 'primary', onClick, disabled }: PropsWithChildren<{ variant?: 'primary' | 'secondary'; onClick?: () => void; disabled?: boolean }>) {
  return (
    <button
      type="button"
      className={`button ${variant === 'secondary' ? 'secondary' : ''}`}
      onClick={onClick}
      disabled={disabled}
    >
      {children}
    </button>
  );
}

type SelectOption = string | { value: string; label: string };

export function Select({ value, onChange, options }: { value: string; onChange: (value: string) => void; options: SelectOption[] }) {
  return (
    <select className="select" value={value} onChange={(event) => onChange(event.target.value)}>
      {options.map((option) => {
        const normalized = typeof option === 'string' ? { value: option, label: option } : option;
        return (
          <option key={normalized.value} value={normalized.value}>
            {normalized.label}
          </option>
        );
      })}
    </select>
  );
}

export function TextInput({ value, onChange, placeholder, onKeyDown, disabled, type = 'text', style }: { value: string; onChange: (value: string) => void; placeholder?: string; onKeyDown?: React.KeyboardEventHandler<HTMLInputElement>; disabled?: boolean; type?: InputHTMLAttributes<HTMLInputElement>['type']; style?: CSSProperties }) {
  return (
    <input
      className="input"
      type={type}
      style={style}
      value={value}
      placeholder={placeholder}
      onKeyDown={onKeyDown}
      disabled={disabled}
      onChange={(event) => onChange(event.target.value)}
    />
  );
}

export function Stat({ value, label, tone }: { value: string; label: string; tone?: string }) {
  const color = tone ? toneColors[tone] ?? '#0f172a' : '#0f172a';
  return (
    <div className="stat">
      <div className="value" style={{ color }}>
        {value}
      </div>
      <div className="label">{label}</div>
    </div>
  );
}

export function Table({ headers, rows, striped = false }: { headers: string[]; rows: (string | number | React.ReactNode)[][]; striped?: boolean }) {
  return (
    <div className="table-wrap">
      <table className={`table ${striped ? 'striped' : ''}`}>
        <thead>
          <tr>
            {headers.map((header) => (
              <th key={header}>{header}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, idx) => (
            <tr key={`${idx}-${row[0]}`}>
              {row.map((cell, cellIdx) => (
                <td key={`${idx}-${cellIdx}`}>{cell}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function CollapsibleSection({ title, count, children }: PropsWithChildren<{ title: string; count?: number }>) {
  return (
    <details>
      <summary style={{ cursor: 'pointer', fontWeight: 600 }}>
        {title} {count ? `(${count})` : ''}
      </summary>
      <div style={{ marginTop: 8 }}>{children}</div>
    </details>
  );
}

export function BarChart({ categories, series, height = 240 }: { categories: string[]; series: { name: string; data: number[]; tone?: string }[]; height?: number }) {
  const data = useMemo(() => {
    return categories.map((category, index) => {
      const entry: Record<string, string | number> = { category };
      series.forEach((item) => {
        entry[item.name] = item.data[index] ?? 0;
      });
      return entry;
    });
  }, [categories, series]);

  return (
    <ResponsiveContainer width="100%" height={height}>
      <ReBarChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
        <XAxis dataKey="category" tick={{ fontSize: 12 }} />
        <YAxis tick={{ fontSize: 12 }} />
        <Tooltip />
        <Legend />
        {series.map((item) => (
          <Bar key={item.name} dataKey={item.name} fill={toneColors[item.tone ?? 'info'] ?? '#2563eb'} radius={[4, 4, 0, 0]} />
        ))}
      </ReBarChart>
    </ResponsiveContainer>
  );
}

export function LineChart({ categories, series, height = 240, fill = false }: { categories: string[]; series: { name: string; data: number[]; tone?: string }[]; height?: number; fill?: boolean }) {
  const data = useMemo(() => {
    return categories.map((category, index) => {
      const entry: Record<string, string | number> = { category };
      series.forEach((item) => {
        entry[item.name] = item.data[index] ?? 0;
      });
      return entry;
    });
  }, [categories, series]);

  return (
    <ResponsiveContainer width="100%" height={height}>
      <ReLineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
        <XAxis dataKey="category" tick={{ fontSize: 12 }} />
        <YAxis tick={{ fontSize: 12 }} />
        <Tooltip />
        <Legend />
        {series.map((item) => (
          <Line
            key={item.name}
            type="monotone"
            dataKey={item.name}
            stroke={toneColors[item.tone ?? 'info'] ?? '#2563eb'}
            strokeWidth={2}
            dot={false}
            fill={fill ? toneColors[item.tone ?? 'info'] ?? '#2563eb' : 'transparent'}
            fillOpacity={0.1}
          />
        ))}
      </ReLineChart>
    </ResponsiveContainer>
  );
}

export function PieChart({ data, height = 240 }: { data: { name: string; value: number; tone?: string }[]; height?: number }) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <RePieChart>
        <Tooltip />
        <Legend />
        <Pie data={data} dataKey="value" nameKey="name" outerRadius={80}>
          {data.map((entry, index) => (
            <Cell key={`${entry.name}-${index}`} fill={toneColors[entry.tone ?? 'info'] ?? '#2563eb'} />
          ))}
        </Pie>
      </RePieChart>
    </ResponsiveContainer>
  );
}
