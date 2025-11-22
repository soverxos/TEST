import { useState, useEffect } from 'react';
import { useI18n } from '../../contexts/I18nContext';
import { Plus, Trash2, CheckCircle2, Circle, AlertCircle } from 'lucide-react';

interface Task {
  id: string;
  title: string;
  completed: boolean;
  priority: 'low' | 'medium' | 'high';
  createdAt: Date;
}

export const TasksWidget = () => {
  const { t } = useI18n();
  const [tasks, setTasks] = useState<Task[]>([]);
  const [newTask, setNewTask] = useState('');
  const [filter, setFilter] = useState<'all' | 'active' | 'completed'>('all');

  useEffect(() => {
    loadTasks();
  }, []);

  const loadTasks = () => {
    const saved = localStorage.getItem('sdb_tasks');
    if (saved) {
      try {
        const parsed = JSON.parse(saved).map((t: any) => ({
          ...t,
          createdAt: new Date(t.createdAt),
        }));
        setTasks(parsed);
      } catch (e) {
        console.error('Error loading tasks:', e);
      }
    }
  };

  const saveTasks = (updatedTasks: Task[]) => {
    localStorage.setItem('sdb_tasks', JSON.stringify(updatedTasks));
    setTasks(updatedTasks);
  };

  const addTask = () => {
    if (!newTask.trim()) return;
    const task: Task = {
      id: Date.now().toString(),
      title: newTask.trim(),
      completed: false,
      priority: 'medium',
      createdAt: new Date(),
    };
    saveTasks([...tasks, task]);
    setNewTask('');
  };

  const toggleTask = (id: string) => {
    saveTasks(tasks.map(t => t.id === id ? { ...t, completed: !t.completed } : t));
  };

  const deleteTask = (id: string) => {
    saveTasks(tasks.filter(t => t.id !== id));
  };

  const filteredTasks = tasks.filter(task => {
    if (filter === 'active') return !task.completed;
    if (filter === 'completed') return task.completed;
    return true;
  });

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high':
        return 'text-red-500';
      case 'medium':
        return 'text-yellow-500';
      case 'low':
        return 'text-green-500';
      default:
        return 'text-gray-500';
    }
  };

  const completedCount = tasks.filter(t => t.completed).length;
  const totalCount = tasks.length;

  return (
    <div className="space-y-3">
      {/* Add Task */}
      <div className="flex gap-2">
        <input
          type="text"
          value={newTask}
          onChange={(e) => setNewTask(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && addTask()}
          placeholder={t('home.tasks.placeholder') || 'Add a task...'}
          className="flex-1 px-3 py-2 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
          style={{
            backgroundColor: 'var(--oneui-bg-alt)',
            borderColor: 'var(--oneui-border)',
            color: 'var(--oneui-text)',
          }}
        />
        <button
          onClick={addTask}
          className="p-2 bg-indigo-500 text-white rounded-lg hover:bg-indigo-600 transition-colors"
        >
          <Plus className="w-4 h-4" />
        </button>
      </div>

      {/* Filter */}
      {tasks.length > 0 && (
        <div className="flex gap-2">
          {(['all', 'active', 'completed'] as const).map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-3 py-1 text-xs rounded transition-colors ${
                filter === f
                  ? 'bg-indigo-500 text-white'
                  : 'bg-gray-100 dark:bg-gray-800 oneui-text-muted hover:bg-gray-200 dark:hover:bg-gray-700'
              }`}
            >
              {t(`home.tasks.${f}`) || f}
            </button>
          ))}
        </div>
      )}

      {/* Progress */}
      {tasks.length > 0 && (
        <div className="flex items-center justify-between text-xs">
          <span className="oneui-text-muted">
            {completedCount} / {totalCount} {t('home.tasks.completed') || 'completed'}
          </span>
          <div className="w-24 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
            <div
              className="h-full bg-green-500 transition-all"
              style={{ width: `${totalCount > 0 ? (completedCount / totalCount) * 100 : 0}%` }}
            />
          </div>
        </div>
      )}

      {/* Tasks List */}
      <div className="space-y-2 max-h-64 overflow-y-auto">
        {filteredTasks.length === 0 ? (
          <div className="text-center py-8">
            <AlertCircle className="w-12 h-12 mx-auto mb-2 oneui-text-muted" />
            <p className="text-sm oneui-text-muted">
              {filter === 'all'
                ? t('home.tasks.noTasks') || 'No tasks yet. Add your first task!'
                : t('home.tasks.noFilteredTasks') || 'No tasks found'}
            </p>
          </div>
        ) : (
          filteredTasks.map((task) => (
            <div
              key={task.id}
              className={`flex items-center gap-3 p-3 rounded-lg border group ${
                task.completed ? 'opacity-60' : ''
              }`}
              style={{
                backgroundColor: 'var(--oneui-bg-alt)',
                borderColor: 'var(--oneui-border)',
              }}
            >
              <button
                onClick={() => toggleTask(task.id)}
                className="flex-shrink-0"
              >
                {task.completed ? (
                  <CheckCircle2 className="w-5 h-5 text-green-500" />
                ) : (
                  <Circle className="w-5 h-5 oneui-text-muted" />
                )}
              </button>
              <div className="flex-1 min-w-0">
                <p
                  className={`text-sm ${
                    task.completed ? 'line-through' : ''
                  }`}
                  style={{ color: 'var(--oneui-text)' }}
                >
                  {task.title}
                </p>
                <div className="flex items-center gap-2 mt-1">
                  <span className={`text-xs ${getPriorityColor(task.priority)}`}>
                    {t(`home.tasks.priority.${task.priority}`) || task.priority}
                  </span>
                </div>
              </div>
              <button
                onClick={() => deleteTask(task.id)}
                className="opacity-0 group-hover:opacity-100 transition-opacity p-1 hover:bg-red-100 dark:hover:bg-red-900 rounded"
                title={t('common.delete') || 'Delete'}
              >
                <Trash2 className="w-4 h-4 text-red-500" />
              </button>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

