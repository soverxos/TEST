import { useState, useEffect } from 'react';
import { useI18n } from '../../contexts/I18nContext';
import { api, Ticket } from '../../api';
import { HelpCircle, MessageSquare, FileText, Send } from 'lucide-react';

export const Support = () => {
  const { t } = useI18n();
  const [activeTab, setActiveTab] = useState<'create' | 'tickets' | 'faq'>('create');
  const [formData, setFormData] = useState({ subject: '', message: '' });
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (activeTab === 'tickets') {
      loadTickets();
    }
  }, [activeTab]);

  const loadTickets = async () => {
    try {
      setLoading(true);
      const data = await api.getTickets();
      setTickets(data);
    } catch (error) {
      console.error('Error loading tickets:', error);
    } finally {
      setLoading(false);
    }
  };

  const faqItems = [
    {
      question: 'Как создать модуль?',
      answer: 'Используйте команду /module create для создания нового модуля.',
    },
    {
      question: 'Как изменить язык интерфейса?',
      answer: 'Нажмите на иконку глобуса в шапке и выберите нужный язык.',
    },
  ];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setSubmitting(true);
      const newTicket = await api.createTicket(formData.subject, formData.message);
      setTickets([newTicket, ...tickets]);
      setFormData({ subject: '', message: '' });
      setActiveTab('tickets');
      alert(t('support.ticketCreated'));
    } catch (error: any) {
      console.error('Error creating ticket:', error);
      alert(`Failed to create ticket: ${error.message || error}`);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div>
      {/* Page Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold mb-2" style={{ color: 'var(--oneui-text)' }}>
          {t('support.title')}
        </h1>
        <p className="oneui-text-muted">{t('support.subtitle')}</p>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 mb-6 border-b" style={{ borderColor: 'var(--oneui-border)' }}>
        {[
          { id: 'create', label: t('support.createTicket'), icon: MessageSquare },
          { id: 'tickets', label: t('support.myTickets'), icon: FileText },
          { id: 'faq', label: t('support.faq'), icon: HelpCircle },
        ].map((tab) => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`px-4 py-2 flex items-center gap-2 border-b-2 transition-colors ${
                activeTab === tab.id
                  ? 'border-indigo-500 text-indigo-600 dark:text-indigo-400'
                  : 'border-transparent oneui-text-muted hover:text-indigo-600 dark:hover:text-indigo-400'
              }`}
            >
              <Icon className="w-4 h-4" />
              <span className="font-medium">{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* Create Ticket */}
      {activeTab === 'create' && (
        <div className="oneui-card">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-2" style={{ color: 'var(--oneui-text)' }}>
                {t('support.subject')}
              </label>
              <input
                type="text"
                value={formData.subject}
                onChange={(e) => setFormData({ ...formData, subject: e.target.value })}
                className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                style={{
                  backgroundColor: 'var(--oneui-bg-alt)',
                  borderColor: 'var(--oneui-border)',
                  color: 'var(--oneui-text)',
                }}
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-2" style={{ color: 'var(--oneui-text)' }}>
                {t('support.message')}
              </label>
              <textarea
                value={formData.message}
                onChange={(e) => setFormData({ ...formData, message: e.target.value })}
                rows={6}
                className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                style={{
                  backgroundColor: 'var(--oneui-bg-alt)',
                  borderColor: 'var(--oneui-border)',
                  color: 'var(--oneui-text)',
                }}
                required
              />
            </div>
            <button 
              type="submit" 
              className="oneui-btn oneui-btn-primary flex items-center gap-2"
              disabled={submitting}
            >
              <Send className="w-4 h-4" />
              {submitting ? t('common.saving') : t('support.submit')}
            </button>
          </form>
        </div>
      )}

      {/* My Tickets */}
      {activeTab === 'tickets' && (
        <div className="oneui-card">
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <div className="oneui-spinner"></div>
            </div>
          ) : tickets.length === 0 ? (
            <div className="text-center py-8 text-sm oneui-text-muted">
              {t('support.noTickets')}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="oneui-table min-w-full">
                <thead>
                  <tr>
                    <th>{t('support.ticketId')}</th>
                    <th>{t('support.subject')}</th>
                    <th>{t('support.status')}</th>
                    <th>{t('support.created')}</th>
                    <th>{t('support.updated')}</th>
                  </tr>
                </thead>
                <tbody>
                  {tickets.map((ticket) => (
                  <tr key={ticket.id}>
                    <td>
                      <code className="text-sm font-mono" style={{ color: 'var(--oneui-text)' }}>
                        {ticket.id}
                      </code>
                    </td>
                    <td className="font-medium" style={{ color: 'var(--oneui-text)' }}>
                      {ticket.subject}
                    </td>
                    <td>
                      <span
                        className={`oneui-badge ${
                          ticket.status === 'open'
                            ? 'oneui-badge-success'
                            : 'oneui-badge-danger'
                        }`}
                      >
                        {ticket.status === 'open' ? t('support.open') : t('support.closed')}
                      </span>
                    </td>
                    <td className="oneui-text-muted">
                      {new Date(ticket.created).toLocaleDateString()}
                    </td>
                    <td className="oneui-text-muted">
                      {new Date(ticket.updated).toLocaleDateString()}
                    </td>
                  </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* FAQ */}
      {activeTab === 'faq' && (
        <div className="space-y-4">
          {faqItems.map((item, index) => (
            <div key={index} className="oneui-card">
              <h3 className="font-semibold mb-2" style={{ color: 'var(--oneui-text)' }}>
                {item.question}
              </h3>
              <p className="text-sm oneui-text-muted">{item.answer}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

