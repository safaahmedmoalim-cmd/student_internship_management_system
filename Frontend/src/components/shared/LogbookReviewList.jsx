import { useState } from 'react';

import { EmptyState, ErrorAlert, Loading } from '../common/ui';
import PromptModal from '../forms/PromptModal';
import LogbookEntry from './LogbookEntry';
import { useAuth } from '../../context/AuthContext';
import { useToast } from '../../context/ToastContext';
import useFetch from '../../hooks/useFetch';
import api from '../../services/api';

const FILTERS = [
  ['pending', 'Awaiting my review'], ['all', 'All entries'], ['rejected', 'Rejected'], ['approved', 'Approved'],
];

/** Logbook review for supervisors; read-only monitoring for the administrator. */
export default function LogbookReviewList() {
  const { user } = useAuth();
  const toast = useToast();
  const isSupervisor = ['academic', 'industrial'].includes(user.role);
  const [filter, setFilter] = useState(isSupervisor ? 'pending' : 'all');
  const [deciding, setDeciding] = useState(null); // {entry, decision}
  const params = filter === 'pending' ? (isSupervisor ? { pending_my_review: 'true' } : { status: 'submitted' })
    : filter === 'all' ? undefined : { status: filter };
  const { data, loading, error, reload } = useFetch('/logbooks/', params);

  const myReview = (e) => e.reviews.find((r) => r.supervisor_role === user.role);
  const filters = isSupervisor ? FILTERS : [['all', 'All entries'], ['pending', 'Submitted'], ['under_review', 'Under review'], ['rejected', 'Rejected'], ['approved', 'Approved']];

  return (
    <>
      <div className="btn-group mb-3 flex-wrap" role="group" aria-label="Filter logbooks">
        {filters.map(([k, label]) => (
          <button key={k} type="button" className={`btn btn-sm ${filter === k ? 'btn-primary' : 'btn-outline-primary'}`} onClick={() => setFilter(k)}>{label}</button>
        ))}
      </div>
      <ErrorAlert error={error} onRetry={reload} />
      {loading ? <Loading /> : (data || []).length === 0 ? <EmptyState icon="journal-check" text="No entries here." /> : (
        data.map((e) => {
          const mine = myReview(e);
          return (
            <LogbookEntry key={e.id} entry={e} showStudent actions={isSupervisor && e.status !== 'approved' && (
              <>
                <button type="button" className="btn btn-sm btn-success" disabled={mine?.review_status === 'approved'}
                  onClick={() => setDeciding({ entry: e, decision: 'approved' })}><i className="bi bi-check-lg me-1" />Approve</button>
                <button type="button" className="btn btn-sm btn-outline-danger" disabled={mine?.review_status === 'rejected'}
                  onClick={() => setDeciding({ entry: e, decision: 'rejected' })}><i className="bi bi-x-lg me-1" />Reject</button>
              </>
            )} />
          );
        })
      )}
      <PromptModal show={Boolean(deciding)}
        title={deciding?.decision === 'approved' ? `Approve week ${deciding?.entry.week_number}` : `Reject week ${deciding?.entry.week_number}`}
        label={deciding?.decision === 'approved' ? 'Comments / feedback (optional)' : 'What must the student correct?'}
        required={deciding?.decision === 'rejected'} variant={deciding?.decision === 'approved' ? 'success' : 'danger'}
        confirmText={deciding?.decision === 'approved' ? 'Approve' : 'Reject'} onClose={() => setDeciding(null)}
        onSubmit={async (comments) => {
          await api.post(`/logbooks/${deciding.entry.id}/review/`, { decision: deciding.decision, comments });
          toast(deciding.decision === 'approved' ? 'Entry approved.' : 'Entry returned to the student.');
          reload();
        }} />
    </>
  );
}
