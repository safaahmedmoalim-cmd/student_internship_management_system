const LABELS = ['', 'Poor', 'Fair', 'Good', 'Very good', 'Excellent'];

/** Rate each criterion 1..max. scores = {criterion: number}. */
export default function ScoreRubric({ criteria, scores, onChange, max = 5, readOnly = false }) {
  const total = criteria.reduce((sum, c) => sum + (Number(scores?.[c]) || 0), 0);
  const complete = criteria.every((c) => scores?.[c]);
  const percent = complete ? Math.round((total * 10000) / (criteria.length * max)) / 100 : null;
  return (
    <div className="table-responsive">
      <table className="table table-sm align-middle rubric">
        <thead>
          <tr>
            <th>Criterion</th>
            {Array.from({ length: max }, (_, i) => <th key={i} className="text-center" title={LABELS[i + 1]}>{i + 1}</th>)}
          </tr>
        </thead>
        <tbody>
          {criteria.map((c) => (
            <tr key={c}>
              <td>{c}</td>
              {Array.from({ length: max }, (_, i) => (
                <td key={i} className="text-center">
                  <input type="radio" className="form-check-input" name={`score-${c}`} aria-label={`${c}: ${i + 1}`}
                    checked={Number(scores?.[c]) === i + 1} disabled={readOnly}
                    onChange={() => onChange?.({ ...scores, [c]: i + 1 })} />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr>
            <th>Total</th>
            <th colSpan={max} className="text-end">
              {total} / {criteria.length * max}{percent !== null && <span className="ms-2 badge bg-primary">{percent}%</span>}
            </th>
          </tr>
        </tfoot>
      </table>
      <div className="small text-muted">1 = Poor · 2 = Fair · 3 = Good · 4 = Very good · 5 = Excellent</div>
    </div>
  );
}
