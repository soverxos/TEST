import { useState } from 'react';
import { useI18n } from '../../contexts/I18nContext';
import { Calculator, Ruler, Hash, Code, ArrowLeftRight, FileText } from 'lucide-react';

type ToolType = 'calculator' | 'converter' | 'encoder' | 'formatter';

export const ToolsWidget = () => {
  const { t } = useI18n();
  const [activeTool, setActiveTool] = useState<ToolType>('calculator');
  const [calcInput, setCalcInput] = useState('');
  const [calcResult, setCalcResult] = useState('');
  const [converterValue, setConverterValue] = useState('');
  const [converterFrom, setConverterFrom] = useState('USD');
  const [converterTo, setConverterTo] = useState('EUR');
  const [encoderInput, setEncoderInput] = useState('');
  const [encoderOutput, setEncoderOutput] = useState('');
  const [encoderType, setEncoderType] = useState<'base64' | 'url' | 'hex'>('base64');

  const tools = [
    { id: 'calculator' as ToolType, icon: Calculator, label: t('home.tools.calculator') || 'Calculator' },
    { id: 'converter' as ToolType, icon: ArrowLeftRight, label: t('home.tools.converter') || 'Converter' },
    { id: 'encoder' as ToolType, icon: Hash, label: t('home.tools.encoder') || 'Encoder' },
    { id: 'formatter' as ToolType, icon: Code, label: t('home.tools.formatter') || 'Formatter' },
  ];

  const handleCalculate = () => {
    try {
      // Simple calculator - in production, use a proper expression parser
      const result = Function(`"use strict"; return (${calcInput})`)();
      setCalcResult(result.toString());
    } catch (e) {
      setCalcResult('Error');
    }
  };

  const handleEncode = () => {
    try {
      switch (encoderType) {
        case 'base64':
          setEncoderOutput(btoa(encoderInput));
          break;
        case 'url':
          setEncoderOutput(encodeURIComponent(encoderInput));
          break;
        case 'hex':
          setEncoderOutput(
            Array.from(encoderInput)
              .map(c => c.charCodeAt(0).toString(16).padStart(2, '0'))
              .join('')
          );
          break;
      }
    } catch (e) {
      setEncoderOutput('Error');
    }
  };

  const handleDecode = () => {
    try {
      switch (encoderType) {
        case 'base64':
          setEncoderInput(atob(encoderOutput));
          break;
        case 'url':
          setEncoderInput(decodeURIComponent(encoderOutput));
          break;
        case 'hex':
          setEncoderInput(
            encoderOutput
              .match(/.{1,2}/g)
              ?.map(byte => String.fromCharCode(parseInt(byte, 16)))
              .join('') || ''
          );
          break;
      }
    } catch (e) {
      setEncoderInput('Error');
    }
  };

  // Mock exchange rates
  const exchangeRates: Record<string, number> = {
    USD: 1,
    EUR: 0.92,
    GBP: 0.79,
    JPY: 149.5,
    RUB: 91.5,
  };

  const convertCurrency = () => {
    const value = parseFloat(converterValue);
    if (isNaN(value)) return;
    const fromRate = exchangeRates[converterFrom] || 1;
    const toRate = exchangeRates[converterTo] || 1;
    const result = (value / fromRate) * toRate;
    return result.toFixed(2);
  };

  return (
    <div className="space-y-3">
      {/* Tool Selector */}
      <div className="grid grid-cols-2 gap-2">
        {tools.map((tool) => {
          const Icon = tool.icon;
          return (
            <button
              key={tool.id}
              onClick={() => setActiveTool(tool.id)}
              className={`flex items-center gap-2 p-2 rounded-lg border transition-colors ${
                activeTool === tool.id
                  ? 'bg-indigo-500 text-white border-indigo-500'
                  : 'bg-gray-50 dark:bg-gray-800 border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-700'
              }`}
            >
              <Icon className="w-4 h-4" />
              <span className="text-xs font-medium">{tool.label}</span>
            </button>
          );
        })}
      </div>

      {/* Calculator */}
      {activeTool === 'calculator' && (
        <div className="space-y-2">
          <input
            type="text"
            value={calcInput}
            onChange={(e) => setCalcInput(e.target.value)}
            placeholder="2 + 2"
            className="w-full px-3 py-2 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
            style={{
              backgroundColor: 'var(--oneui-bg-alt)',
              borderColor: 'var(--oneui-border)',
              color: 'var(--oneui-text)',
            }}
          />
          <button
            onClick={handleCalculate}
            className="w-full px-4 py-2 text-sm bg-indigo-500 text-white rounded-lg hover:bg-indigo-600 transition-colors"
          >
            {t('home.tools.calculate') || 'Calculate'}
          </button>
          {calcResult && (
            <div className="p-3 rounded-lg" style={{ backgroundColor: 'var(--oneui-bg-alt)' }}>
              <p className="text-sm oneui-text-muted mb-1">{t('home.tools.result') || 'Result'}</p>
              <p className="text-lg font-bold" style={{ color: 'var(--oneui-text)' }}>
                {calcResult}
              </p>
            </div>
          )}
        </div>
      )}

      {/* Currency Converter */}
      {activeTool === 'converter' && (
        <div className="space-y-2">
          <div className="flex gap-2">
            <input
              type="number"
              value={converterValue}
              onChange={(e) => setConverterValue(e.target.value)}
              placeholder="100"
              className="flex-1 px-3 py-2 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
              style={{
                backgroundColor: 'var(--oneui-bg-alt)',
                borderColor: 'var(--oneui-border)',
                color: 'var(--oneui-text)',
              }}
            />
            <select
              value={converterFrom}
              onChange={(e) => setConverterFrom(e.target.value)}
              className="px-3 py-2 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
              style={{
                backgroundColor: 'var(--oneui-bg-alt)',
                borderColor: 'var(--oneui-border)',
                color: 'var(--oneui-text)',
              }}
            >
              {Object.keys(exchangeRates).map(currency => (
                <option key={currency} value={currency}>{currency}</option>
              ))}
            </select>
          </div>
          <div className="flex items-center justify-center">
            <ArrowLeftRight className="w-4 h-4 oneui-text-muted" />
          </div>
          <div className="flex gap-2">
            <div className="flex-1 px-3 py-2 text-sm border rounded-lg" style={{ backgroundColor: 'var(--oneui-bg-alt)', borderColor: 'var(--oneui-border)' }}>
              <p className="text-xs oneui-text-muted mb-1">{t('home.tools.result') || 'Result'}</p>
              <p className="text-lg font-bold" style={{ color: 'var(--oneui-text)' }}>
                {converterValue ? convertCurrency() : '0.00'}
              </p>
            </div>
            <select
              value={converterTo}
              onChange={(e) => setConverterTo(e.target.value)}
              className="px-3 py-2 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
              style={{
                backgroundColor: 'var(--oneui-bg-alt)',
                borderColor: 'var(--oneui-border)',
                color: 'var(--oneui-text)',
              }}
            >
              {Object.keys(exchangeRates).map(currency => (
                <option key={currency} value={currency}>{currency}</option>
              ))}
            </select>
          </div>
        </div>
      )}

      {/* Encoder/Decoder */}
      {activeTool === 'encoder' && (
        <div className="space-y-2">
          <select
            value={encoderType}
            onChange={(e) => setEncoderType(e.target.value as any)}
            className="w-full px-3 py-2 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
            style={{
              backgroundColor: 'var(--oneui-bg-alt)',
              borderColor: 'var(--oneui-border)',
              color: 'var(--oneui-text)',
            }}
          >
            <option value="base64">Base64</option>
            <option value="url">URL</option>
            <option value="hex">Hex</option>
          </select>
          <textarea
            value={encoderInput}
            onChange={(e) => setEncoderInput(e.target.value)}
            placeholder={t('home.tools.input') || 'Input'}
            className="w-full px-3 py-2 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
            style={{
              backgroundColor: 'var(--oneui-bg-alt)',
              borderColor: 'var(--oneui-border)',
              color: 'var(--oneui-text)',
            }}
            rows={3}
          />
          <div className="flex gap-2">
            <button
              onClick={handleEncode}
              className="flex-1 px-4 py-2 text-sm bg-indigo-500 text-white rounded-lg hover:bg-indigo-600 transition-colors"
            >
              {t('home.tools.encode') || 'Encode'}
            </button>
            <button
              onClick={handleDecode}
              className="flex-1 px-4 py-2 text-sm bg-gray-500 text-white rounded-lg hover:bg-gray-600 transition-colors"
            >
              {t('home.tools.decode') || 'Decode'}
            </button>
          </div>
          <textarea
            value={encoderOutput}
            onChange={(e) => setEncoderOutput(e.target.value)}
            placeholder={t('home.tools.output') || 'Output'}
            className="w-full px-3 py-2 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
            style={{
              backgroundColor: 'var(--oneui-bg-alt)',
              borderColor: 'var(--oneui-border)',
              color: 'var(--oneui-text)',
            }}
            rows={3}
          />
        </div>
      )}

      {/* Formatter */}
      {activeTool === 'formatter' && (
        <div className="text-center py-8">
          <FileText className="w-12 h-12 mx-auto mb-2 oneui-text-muted" />
          <p className="text-sm oneui-text-muted">
            {t('home.tools.formatterComingSoon') || 'Formatter coming soon'}
          </p>
        </div>
      )}
    </div>
  );
};

