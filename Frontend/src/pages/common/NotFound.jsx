import { Link } from 'react-router-dom';

import { EmptyState } from '../../components/common/ui';

export default function NotFound() {
  return (
    <EmptyState icon="signpost-split" text="This page does not exist.">
      <Link to="/" className="btn btn-primary">Go to my dashboard</Link>
    </EmptyState>
  );
}
