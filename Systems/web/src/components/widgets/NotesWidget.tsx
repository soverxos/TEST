import { useState, useEffect } from 'react';
import { useI18n } from '../../contexts/I18nContext';
import { Plus, Trash2, Edit2, Save, X } from 'lucide-react';

interface Note {
  id: string;
  content: string;
  createdAt: Date;
  updatedAt: Date;
}

export const NotesWidget = () => {
  const { t } = useI18n();
  const [notes, setNotes] = useState<Note[]>([]);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editContent, setEditContent] = useState('');
  const [newNote, setNewNote] = useState('');

  useEffect(() => {
    loadNotes();
  }, []);

  const loadNotes = () => {
    const saved = localStorage.getItem('sdb_notes');
    if (saved) {
      try {
        const parsed = JSON.parse(saved).map((n: any) => ({
          ...n,
          createdAt: new Date(n.createdAt),
          updatedAt: new Date(n.updatedAt),
        }));
        setNotes(parsed);
      } catch (e) {
        console.error('Error loading notes:', e);
      }
    }
  };

  const saveNotes = (updatedNotes: Note[]) => {
    localStorage.setItem('sdb_notes', JSON.stringify(updatedNotes));
    setNotes(updatedNotes);
  };

  const addNote = () => {
    if (!newNote.trim()) return;
    const note: Note = {
      id: Date.now().toString(),
      content: newNote.trim(),
      createdAt: new Date(),
      updatedAt: new Date(),
    };
    saveNotes([...notes, note]);
    setNewNote('');
  };

  const deleteNote = (id: string) => {
    saveNotes(notes.filter(n => n.id !== id));
  };

  const startEdit = (note: Note) => {
    setEditingId(note.id);
    setEditContent(note.content);
  };

  const saveEdit = () => {
    if (!editingId || !editContent.trim()) return;
    saveNotes(notes.map(n =>
      n.id === editingId
        ? { ...n, content: editContent.trim(), updatedAt: new Date() }
        : n
    ));
    setEditingId(null);
    setEditContent('');
  };

  const cancelEdit = () => {
    setEditingId(null);
    setEditContent('');
  };

  return (
    <div className="space-y-3">
      {/* Add Note */}
      <div className="flex gap-2">
        <input
          type="text"
          value={newNote}
          onChange={(e) => setNewNote(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && addNote()}
          placeholder={t('home.notes.placeholder') || 'Add a note...'}
          className="flex-1 px-3 py-2 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
          style={{
            backgroundColor: 'var(--oneui-bg-alt)',
            borderColor: 'var(--oneui-border)',
            color: 'var(--oneui-text)',
          }}
        />
        <button
          onClick={addNote}
          className="p-2 bg-indigo-500 text-white rounded-lg hover:bg-indigo-600 transition-colors"
        >
          <Plus className="w-4 h-4" />
        </button>
      </div>

      {/* Notes List */}
      <div className="space-y-2 max-h-64 overflow-y-auto">
        {notes.length === 0 ? (
          <div className="text-center py-8">
            <p className="text-sm oneui-text-muted">
              {t('home.notes.noNotes') || 'No notes yet. Add your first note!'}
            </p>
          </div>
        ) : (
          notes.map((note) => (
            <div
              key={note.id}
              className="p-3 rounded-lg border group"
              style={{
                backgroundColor: 'var(--oneui-bg-alt)',
                borderColor: 'var(--oneui-border)',
              }}
            >
              {editingId === note.id ? (
                <div className="space-y-2">
                  <textarea
                    value={editContent}
                    onChange={(e) => setEditContent(e.target.value)}
                    className="w-full px-2 py-1 text-sm border rounded focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    style={{
                      backgroundColor: 'var(--oneui-bg)',
                      borderColor: 'var(--oneui-border)',
                      color: 'var(--oneui-text)',
                    }}
                    rows={3}
                  />
                  <div className="flex gap-2">
                    <button
                      onClick={saveEdit}
                      className="flex items-center gap-1 px-2 py-1 text-xs bg-green-500 text-white rounded hover:bg-green-600"
                    >
                      <Save className="w-3 h-3" />
                      {t('common.save') || 'Save'}
                    </button>
                    <button
                      onClick={cancelEdit}
                      className="flex items-center gap-1 px-2 py-1 text-xs bg-gray-500 text-white rounded hover:bg-gray-600"
                    >
                      <X className="w-3 h-3" />
                      {t('common.cancel') || 'Cancel'}
                    </button>
                  </div>
                </div>
              ) : (
                <>
                  <p className="text-sm" style={{ color: 'var(--oneui-text)' }}>
                    {note.content}
                  </p>
                  <div className="flex items-center justify-between mt-2">
                    <span className="text-xs oneui-text-muted">
                      {note.updatedAt.toLocaleDateString()}
                    </span>
                    <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                      <button
                        onClick={() => startEdit(note)}
                        className="p-1 hover:bg-gray-100 dark:hover:bg-gray-800 rounded"
                        title={t('common.edit') || 'Edit'}
                      >
                        <Edit2 className="w-3 h-3 oneui-text-muted" />
                      </button>
                      <button
                        onClick={() => deleteNote(note.id)}
                        className="p-1 hover:bg-red-100 dark:hover:bg-red-900 rounded"
                        title={t('common.delete') || 'Delete'}
                      >
                        <Trash2 className="w-3 h-3 text-red-500" />
                      </button>
                    </div>
                  </div>
                </>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
};

