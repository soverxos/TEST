import { useState } from 'react';
import { X, Plus, Check } from 'lucide-react';
import { useI18n } from '../../contexts/I18nContext';

export type WidgetType = 'stats' | 'activity' | 'systemHealth' | 'custom';

export interface WidgetConfig {
  id: string;
  type: WidgetType;
  title: string;
  enabled: boolean;
  order: number;
}

interface WidgetSettingsProps {
  availableWidgets: WidgetConfig[];
  enabledWidgets: string[];
  onClose: () => void;
  onSave: (enabledIds: string[]) => void;
}

export const WidgetSettings = ({
  availableWidgets,
  enabledWidgets,
  onClose,
  onSave,
}: WidgetSettingsProps) => {
  const { t } = useI18n();
  const [selected, setSelected] = useState<string[]>(enabledWidgets);

  const toggleWidget = (id: string) => {
    setSelected(prev =>
      prev.includes(id) ? prev.filter(w => w !== id) : [...prev, id]
    );
  };

  const handleSave = () => {
    onSave(selected);
    onClose();
  };

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="oneui-card max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <div className="oneui-card-header flex items-center justify-between">
          <h3 className="oneui-card-title">{t('home.widgetSettings') || 'Widget Settings'}</h3>
          <button
            onClick={onClose}
            className="p-1 hover:bg-gray-100 dark:hover:bg-gray-800 rounded transition-colors"
          >
            <X className="w-5 h-5 oneui-text-muted" />
          </button>
        </div>
        
        <div className="space-y-2 p-4">
          <p className="text-sm oneui-text-muted mb-4">
            {t('home.widgetSettingsDesc') || 'Select widgets to display on the home page'}
          </p>
          
          {availableWidgets.map((widget) => (
            <div
              key={widget.id}
              onClick={() => toggleWidget(widget.id)}
              className={`flex items-center justify-between p-4 rounded-lg cursor-pointer transition-colors ${
                selected.includes(widget.id)
                  ? 'bg-indigo-500/20 border-2 border-indigo-500'
                  : 'bg-gray-50 dark:bg-gray-800 border-2 border-transparent hover:bg-gray-100 dark:hover:bg-gray-700'
              }`}
            >
              <div className="flex items-center gap-3">
                {selected.includes(widget.id) && (
                  <div className="w-5 h-5 rounded-full bg-indigo-500 flex items-center justify-center">
                    <Check className="w-3 h-3 text-white" />
                  </div>
                )}
                {!selected.includes(widget.id) && (
                  <div className="w-5 h-5 rounded-full border-2 border-gray-300 dark:border-gray-600" />
                )}
                <div>
                  <p className="font-medium" style={{ color: 'var(--oneui-text)' }}>
                    {widget.title}
                  </p>
                  <p className="text-xs oneui-text-muted">
                    {t(`home.widget.${widget.id}.desc`) || t(`home.widget.${widget.type}.desc`) || `Widget type: ${widget.type}`}
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>

        <div className="oneui-card-footer flex justify-end gap-2">
          <button
            onClick={onClose}
            className="oneui-btn oneui-btn-secondary"
          >
            {t('common.cancel') || 'Cancel'}
          </button>
          <button
            onClick={handleSave}
            className="oneui-btn oneui-btn-primary flex items-center gap-2"
          >
            <Check className="w-4 h-4" />
            {t('common.save') || 'Save'}
          </button>
        </div>
      </div>
    </div>
  );
};

