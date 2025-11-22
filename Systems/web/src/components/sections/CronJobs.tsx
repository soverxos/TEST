import { useState, useEffect } from 'react';
import { useI18n } from '../../contexts/I18nContext';
import { api, CronJob } from '../../api';
import { Clock, RefreshCw, Calendar, Play } from 'lucide-react';

export const CronJobs = () => {
  const { t } = useI18n();
  const [jobs, setJobs] = useState<CronJob[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadJobs();
    // Refresh every 30 seconds
    const interval = setInterval(loadJobs, 30000);
    return () => clearInterval(interval);
  }, []);

  const loadJobs = async () => {
    try {
      const data = await api.getCronJobs();
      setJobs(data || []);
    } catch (error) {
      console.error('Error loading cron jobs:', error);
    } finally {
      setLoading(false);
    }
  };

  const formatNextRun = (nextRunTime: string | null) => {
    if (!nextRunTime) return t('cronJobs.never') || 'Never';
    try {
      const date = new Date(nextRunTime);
      return date.toLocaleString();
    } catch {
      return nextRunTime;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="oneui-spinner"></div>
      </div>
    );
  }

  return (
    <div>
      {/* Page Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold mb-2" style={{ color: 'var(--oneui-text)' }}>
          {t('cronJobs.title') || 'Scheduled Jobs'}
        </h1>
        <p className="oneui-text-muted">
          {t('cronJobs.subtitle') || 'View and manage scheduled tasks (APScheduler)'}
        </p>
      </div>

      {/* Jobs List */}
      <div className="oneui-card">
        <div className="oneui-card-header">
          <div className="flex items-center justify-between w-full">
            <div className="flex items-center gap-3">
              <div className="oneui-stat-icon oneui-stat-icon-primary">
                <Clock className="w-5 h-5" />
              </div>
              <h3 className="oneui-card-title">
                {t('cronJobs.scheduledJobs') || 'Scheduled Jobs'}
              </h3>
            </div>
            <button
              onClick={loadJobs}
              className="oneui-btn oneui-btn-secondary text-sm flex items-center gap-2"
            >
              <RefreshCw className="w-4 h-4" />
              {t('common.refresh') || 'Refresh'}
            </button>
          </div>
        </div>

        {jobs.length === 0 ? (
          <div className="text-center py-12">
            <Clock className="w-16 h-16 mx-auto mb-4 oneui-text-muted" />
            <h3 className="text-xl font-bold mb-2" style={{ color: 'var(--oneui-text)' }}>
              {t('cronJobs.noJobs') || 'No scheduled jobs'}
            </h3>
            <p className="oneui-text-muted">
              {t('cronJobs.noJobsDesc') || 'No cron jobs are currently scheduled.'}
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="oneui-table min-w-full">
              <thead>
                <tr>
                  <th>{t('cronJobs.jobName') || 'Job Name'}</th>
                  <th>{t('cronJobs.function') || 'Function'}</th>
                  <th>{t('cronJobs.trigger') || 'Trigger'}</th>
                  <th>{t('cronJobs.nextRun') || 'Next Run'}</th>
                </tr>
              </thead>
              <tbody>
                {jobs.map((job) => (
                  <tr key={job.id}>
                    <td className="font-medium" style={{ color: 'var(--oneui-text)' }}>
                      <div className="flex items-center gap-2">
                        <Calendar className="w-4 h-4 oneui-text-muted" />
                        {job.name}
                      </div>
                    </td>
                    <td className="oneui-text-muted">
                      <code className="text-sm font-mono">{job.func}</code>
                    </td>
                    <td className="oneui-text-muted">
                      {job.trigger || '-'}
                    </td>
                    <td className="oneui-text-muted">
                      <div className="flex items-center gap-2">
                        <Play className="w-4 h-4" />
                        {formatNextRun(job.next_run_time)}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

