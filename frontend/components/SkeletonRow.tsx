export default function SkeletonRow({ className = "" }: { className?: string }) {
  return <div aria-hidden="true" className={`h-4 animate-pulse bg-sunk ${className}`} />;
}
