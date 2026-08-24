import { useQueryClient } from '@tanstack/react-query';
import { useDatasetConfirm } from '../hooks/useDatasets';
import { Button } from '@/components/ui/button';

interface DatasetConfirmButtonProps {
  datasetId: string;
  status: string;
  onConfirmed?: () => void;
}

const REVIEW_REQUIRED_STATUS = 'REVIEW_REQUIRED';

/**
 * DatasetConfirmButton — Allows confirming a dataset that requires review.
 * Only visible when dataset status is REVIEW_REQUIRED.
 * On success, invalidates the datasets query cache and calls onConfirmed callback.
 */
export function DatasetConfirmButton({
  datasetId,
  status,
  onConfirmed,
}: DatasetConfirmButtonProps) {
  const queryClient = useQueryClient();
  const confirmMutation = useDatasetConfirm();

  if (status !== REVIEW_REQUIRED_STATUS) {
    return null;
  }

  const handleConfirm = () => {
    confirmMutation.mutate(
      { id: datasetId },
      {
        onSuccess: () => {
          void queryClient.invalidateQueries({ queryKey: ['datasets'] });
          onConfirmed?.();
        },
      },
    );
  };

  return (
    <Button
      onClick={handleConfirm}
      disabled={confirmMutation.isPending}
      size="sm"
      className="bg-green-600 text-white hover:bg-green-700 disabled:opacity-50"
      aria-label={`Confirm dataset ${datasetId}`}
    >
      {confirmMutation.isPending ? 'Confirming…' : 'Confirm'}
    </Button>
  );
}
