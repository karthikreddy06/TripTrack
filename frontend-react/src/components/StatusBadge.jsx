export const StatusBadge = ({ status = 'planned' }) => {
  const normalizedStatus = (status || 'planned').toLowerCase();

  return (
    <span className={`status-badge status-${normalizedStatus}`}>
      <span className="status-badge-dot" />
      {normalizedStatus}
    </span>
  );
};
