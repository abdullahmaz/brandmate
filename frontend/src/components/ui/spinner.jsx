import { Spinner as ShadcnSpinner } from './shadcn-io/spinner';

export function Spinner({ variant = 'ellipsis', size = 20, className, ...props }) {
  return <ShadcnSpinner variant={variant} size={size} className={className} {...props} />;
}
