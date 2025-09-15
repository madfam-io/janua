'use client';

import React, { useState, useEffect } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { CheckCircle, AlertCircle } from 'lucide-react';

interface Version {
  id: string;
  label: string;
  status: 'stable' | 'beta' | 'deprecated' | 'experimental';
  releaseDate?: string;
  endOfLife?: string;
}

interface VersionSelectorProps {
  versions?: Version[];
  currentVersion?: string;
  onVersionChange?: (version: string) => void;
}

const defaultVersions: Version[] = [
  {
    id: 'v2',
    label: 'v2.0',
    status: 'stable',
    releaseDate: '2024-01-15'
  },
  {
    id: 'v1',
    label: 'v1.0',
    status: 'deprecated',
    releaseDate: '2023-06-01',
    endOfLife: '2024-06-01'
  },
  {
    id: 'v3-beta',
    label: 'v3.0-beta',
    status: 'beta',
    releaseDate: '2024-02-01'
  }
];

export function VersionSelector({
  versions = defaultVersions,
  currentVersion = 'v2',
  onVersionChange
}: VersionSelectorProps) {
  const router = useRouter();
  const pathname = usePathname();
  const [selectedVersion, setSelectedVersion] = useState(currentVersion);
  const [showWarning, setShowWarning] = useState(false);

  useEffect(() => {
    // Check if current version is deprecated or experimental
    const current = versions.find(v => v.id === selectedVersion);
    if (current && (current.status === 'deprecated' || current.status === 'experimental')) {
      setShowWarning(true);
    } else {
      setShowWarning(false);
    }
  }, [selectedVersion, versions]);

  const handleVersionChange = (newVersion: string) => {
    setSelectedVersion(newVersion);

    // Construct new URL with version
    const newPath = pathname.replace(/\/v\d+(-\w+)?/, '') || '/';
    const versionedPath = `/${newVersion}${newPath}`;

    // Call custom handler if provided
    if (onVersionChange) {
      onVersionChange(newVersion);
    } else {
      // Default behavior: navigate to versioned path
      router.push(versionedPath);
    }
  };

  const getStatusBadge = (status: Version['status']) => {
    switch (status) {
      case 'stable':
        return (
          <Badge variant="default" className="ml-2">
            <CheckCircle className="h-3 w-3 mr-1" />
            Stable
          </Badge>
        );
      case 'beta':
        return (
          <Badge variant="secondary" className="ml-2">
            Beta
          </Badge>
        );
      case 'deprecated':
        return (
          <Badge variant="destructive" className="ml-2">
            <AlertCircle className="h-3 w-3 mr-1" />
            Deprecated
          </Badge>
        );
      case 'experimental':
        return (
          <Badge variant="outline" className="ml-2">
            Experimental
          </Badge>
        );
      default:
        return null;
    }
  };

  const currentVersionData = versions.find(v => v.id === selectedVersion);

  return (
    <div className="space-y-2">
      <Select value={selectedVersion} onValueChange={handleVersionChange}>
        <SelectTrigger className="w-[180px]">
          <SelectValue>
            <div className="flex items-center">
              <span>{currentVersionData?.label}</span>
              {currentVersionData && getStatusBadge(currentVersionData.status)}
            </div>
          </SelectValue>
        </SelectTrigger>
        <SelectContent>
          {versions.map((version) => (
            <SelectItem key={version.id} value={version.id}>
              <div className="flex items-center justify-between w-full">
                <span>{version.label}</span>
                {getStatusBadge(version.status)}
              </div>
              {version.releaseDate && (
                <span className="text-xs text-muted-foreground ml-2">
                  Released {new Date(version.releaseDate).toLocaleDateString()}
                </span>
              )}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      {showWarning && currentVersionData && (
        <div className={`p-3 rounded-md text-sm ${
          currentVersionData.status === 'deprecated'
            ? 'bg-destructive/10 border border-destructive/20 text-destructive'
            : 'bg-yellow-100/10 border border-yellow-200/20 text-yellow-800 dark:text-yellow-200'
        }`}>
          {currentVersionData.status === 'deprecated' ? (
            <>
              <strong>Warning:</strong> This version is deprecated
              {currentVersionData.endOfLife && (
                <> and will reach end of life on {new Date(currentVersionData.endOfLife).toLocaleDateString()}</>
              )}.
              Please upgrade to the latest stable version.
            </>
          ) : currentVersionData.status === 'experimental' ? (
            <>
              <strong>Note:</strong> This is an experimental version and may contain breaking changes.
              Use in production at your own risk.
            </>
          ) : (
            <>
              <strong>Note:</strong> This is a beta version and may contain bugs.
              For production use, please use the stable version.
            </>
          )}
        </div>
      )}
    </div>
  );
}

// Inline version badge component for use in documentation
export function VersionBadge({ version, minimal = false }: { version: string; minimal?: boolean }) {
  const versionData = defaultVersions.find(v => v.id === version);

  if (!versionData) {
    return <Badge variant="outline">{version}</Badge>;
  }

  if (minimal) {
    return <Badge variant="outline">{versionData.label}</Badge>;
  }

  const variantMap = {
    stable: 'default',
    beta: 'secondary',
    deprecated: 'destructive',
    experimental: 'outline'
  } as const;

  return (
    <Badge variant={variantMap[versionData.status]}>
      {versionData.label}
      {versionData.status !== 'stable' && ` (${versionData.status})`}
    </Badge>
  );
}