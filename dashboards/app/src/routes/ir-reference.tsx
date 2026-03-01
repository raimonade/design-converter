import { createFileRoute } from '@tanstack/react-router';
import { IRReference } from '@/pages/IRReference';

export const Route = createFileRoute('/ir-reference')({
  component: IRReference,
});
