import { ReactNode } from 'react';
import { GripVertical, X } from 'lucide-react';

interface WidgetContainerProps {
  id: string;
  title: string;
  children: ReactNode;
  onRemove?: () => void;
  isDragging?: boolean;
  onDragStart?: (e: React.DragEvent) => void;
  onDragOver?: (e: React.DragEvent) => void;
  onDrop?: (e: React.DragEvent) => void;
  onDragEnd?: () => void;
}

export const WidgetContainer = ({
  id,
  title,
  children,
  onRemove,
  isDragging = false,
  onDragStart,
  onDragOver,
  onDrop,
  onDragEnd,
}: WidgetContainerProps) => {
  const handleDragStart = (e: React.DragEvent) => {
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', id);
    if (onDragStart) onDragStart(e);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    if (onDragOver) onDragOver(e);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (onDrop) onDrop(e);
  };

  return (
    <div
      draggable
      onDragStart={handleDragStart}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
      onDragEnd={onDragEnd}
      className={`oneui-card relative group ${isDragging ? 'opacity-50' : ''}`}
      style={{ cursor: 'move' }}
    >
      {/* Widget Header */}
      <div className="oneui-card-header flex items-center justify-between">
        <div className="flex items-center gap-2 flex-1">
          <GripVertical className="w-4 h-4 oneui-text-muted cursor-move" />
          <h3 className="oneui-card-title">{title}</h3>
        </div>
        {onRemove && (
          <button
            onClick={onRemove}
            className="opacity-0 group-hover:opacity-100 transition-opacity p-1 hover:bg-gray-100 dark:hover:bg-gray-800 rounded"
            title="Remove widget"
          >
            <X className="w-4 h-4 oneui-text-muted" />
          </button>
        )}
      </div>
      
      {/* Widget Content */}
      <div className="oneui-card-content">
        {children}
      </div>
    </div>
  );
};

