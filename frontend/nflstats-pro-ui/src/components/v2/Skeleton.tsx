import React from 'react';
import { motion } from 'framer-motion';
import { cn } from '../../utils/cn';
 // I'll create this utility

interface SkeletonProps {
  className?: string;
  count?: number;
}

export const Skeleton: React.FC<SkeletonProps> = ({ className, count = 1 }) => {
  return (
    <>
      {Array.from({ length: count }).map((_, i) => (
        <motion.div
          key={i}
          initial={{ opacity: 0.5 }}
          animate={{ opacity: [0.5, 0.8, 0.5] }}
          transition={{
            duration: 2,
            repeat: Infinity,
            ease: "easeInOut",
          }}
          className={cn("bg-slate-800/50 rounded-md animate-pulse", className)}
        />
      ))}
    </>
  );
};

export const TableSkeleton: React.FC = () => {
  return (
    <div className="w-full space-y-4 p-4">
      <Skeleton className="h-10 w-full" />
      <div className="space-y-2">
        <Skeleton className="h-12 w-full" count={10} />
      </div>
    </div>
  );
};
