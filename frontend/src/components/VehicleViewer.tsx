import { useState } from 'react';
import { Vehicle3DViewer } from './Vehicle3DViewer';
import type { ComponentHighlight, Vehicle3DViewerProps } from './Vehicle3DViewer';
import { cn } from '../utils/cn';

export type { ComponentHighlight };

interface ViewControl {
  key: string;
  label: string;
  icon: string;
}

const VIEW_CONTROLS: ViewControl[] = [
  { key: 'overview', label: 'Exterior', icon: 'directions_car' },
  { key: 'engine_bay', label: 'Diagnostic', icon: 'build' },
  { key: 'underbody', label: 'X-Ray', icon: 'visibility' },
];

/**
 * Stitch-inspired 3D vehicle hero. Wraps the independent, functional
 * Vehicle3DViewer (React Three Fiber + GLB) with HUD overlays:
 * a status pill, view-control buttons, and a focus reticle.
 */
export function VehicleViewer({
  vehicleType = 'sedan',
  highlightedComponents = [],
  selectedComponent = null,
  onComponentSelect,
  className,
  height = 420,
}: Vehicle3DViewerProps) {
  const [preset, setPreset] = useState<string>('overview');

  return (
    <div
      className={cn(
        'relative overflow-hidden rounded-lg border border-outline-variant bg-surface-container-lowest',
        className
      )}
    >
      <Vehicle3DViewer
        vehicleType={vehicleType}
        highlightedComponents={highlightedComponents}
        selectedComponent={selectedComponent}
        onComponentSelect={onComponentSelect}
        height={height}
        hideControls
        activePreset={preset}
        onPresetChange={setPreset}
      />

      {/* Status pill (HUD) */}
      <div className="pointer-events-none absolute left-4 top-4 z-20">
        <div className="hud-panel corner-brackets flex items-center gap-2 px-3 py-1.5 shadow-sm">
          <span className="material-symbols-outlined text-sm text-primary">sensors</span>
          <span className="font-data-mono text-xs text-primary">SYS_SCAN_ACTIVE</span>
        </div>
      </div>

      {/* View controls (HUD) */}
      <div className="absolute right-4 top-4 z-20 flex flex-col gap-1">
        {VIEW_CONTROLS.map((view) => {
          const active = preset === view.key;
          return (
            <button
              key={view.key}
              type="button"
              aria-label={view.label}
              aria-pressed={active}
              onClick={() => setPreset(view.key)}
              className={cn(
                'hud-panel corner-brackets p-1.5 transition-colors active:scale-95',
                active
                  ? 'bg-primary-container text-on-primary-container'
                  : 'text-on-surface-variant hover:text-primary'
              )}
            >
              <span className="material-symbols-outlined text-sm">{view.icon}</span>
            </button>
          );
        })}
      </div>

      {/* Focus reticle (HUD, decorative) */}
      <div
        className="pointer-events-none absolute inset-0 z-10 flex items-center justify-center"
        style={{ transform: 'translate(-10%, 15%)' }}
        aria-hidden="true"
      >
        <div className="relative flex h-24 w-24 items-center justify-center rounded-full border border-secondary/40">
          <span className="h-1 w-1 rounded-full bg-secondary" />
          <span className="absolute left-1/2 top-0 h-1/2 w-px -translate-x-1/2 bg-secondary/20" />
          <span className="absolute left-1/2 bottom-0 h-1/2 w-px -translate-x-1/2 bg-secondary/20" />
          <span className="absolute top-1/2 left-0 h-px w-1/2 -translate-y-1/2 bg-secondary/20" />
          <span className="absolute top-1/2 right-0 h-px w-1/2 -translate-y-1/2 bg-secondary/20" />
        </div>
      </div>
    </div>
  );
}
