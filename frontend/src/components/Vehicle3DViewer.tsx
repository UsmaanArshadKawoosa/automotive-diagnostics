import type { ReactNode } from 'react';
import * as React from 'react';
import { Suspense, useMemo, useRef, useEffect, useCallback } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { OrbitControls, useGLTF } from '@react-three/drei';
import { OrbitControls as OrbitControlsImpl } from 'three-stdlib';
import * as THREE from 'three';
import { getVehicleTypeConfig } from '../config/vehicleTypes';
import { resolveNodeNamesForComponent, type VehicleType, getComponentCameraTarget } from '../config/glbMeshMapping';

export interface ComponentHighlight {
  component_id: string;
  system_category?: string;
  vehicle_region?: string;
  safety_tier?: 'diy_inspection' | 'diy_repair' | 'mechanic_recommended' | 'immediate_professional';
  safety_tier_label?: string;
  safety_tier_description?: string;
  safety_tier_reasoning?: string[];
}

export interface Vehicle3DViewerProps {
  vehicleType?: VehicleType;
  highlightedComponents?: ComponentHighlight[];
  selectedComponent?: ComponentHighlight | null;
  onComponentSelect?: (component: ComponentHighlight | null) => void;
  className?: string;
  children?: ReactNode;
}

const SAFETY_TIER_COLORS: Record<string, string> = {
  diy_inspection: 'bg-green-500',
  diy_repair: 'bg-amber-500',
  mechanic_recommended: 'bg-orange-500',
  immediate_professional: 'bg-red-500',
  default: 'bg-slate-500',
};

const SAFETY_TIER_LABELS: Record<string, string> = {
  diy_inspection: 'Safe to inspect yourself',
  diy_repair: 'DIY repair may be possible',
  mechanic_recommended: 'Mechanic recommended',
  immediate_professional: 'Seek professional service immediately',
};

const SAFETY_TIER_ACTIONS: Record<string, string> = {
  diy_inspection: 'Inspect the component visually and check for obvious issues.',
  diy_repair: 'Repair may be possible with appropriate tools and service manual guidance.',
  mechanic_recommended: 'Schedule service with a qualified mechanic.',
  immediate_professional: 'Do not drive. Contact a professional immediately.',
};

const REGION_COLORS: Record<string, number> = {
  engine_bay: 0x808080,
  intake: 0x654321,
  exhaust: 0x2f2f2f,
  underbody: 0x4b4b4b,
  fuel_tank: 0x000080,
  transmission: 0x8b4513,
  chassis: 0x2f4f4f,
  default: 0xcccccc,
};

const REGION_SIZES: Record<string, [number, number, number]> = {
  engine_bay: [4, 2, 2],
  intake: [2, 1.5, 1],
  exhaust: [3, 1, 1],
  underbody: [5, 0.5, 2.5],
  fuel_tank: [3, 2, 1.5],
  transmission: [2, 1.5, 1],
  chassis: [6, 0.3, 2.5],
  default: [1, 1, 1],
};

const REGION_POSITIONS: Record<string, [number, number, number]> = {
  engine_bay: [0, 1, 0],
  intake: [-2, 0.5, 1.5],
  exhaust: [2, 0, -2],
  underbody: [0, -0.2, 0],
  fuel_tank: [0, 0.5, -1.5],
  transmission: [0, 0.5, 1.5],
  chassis: [0, -0.4, 0],
  default: [0, 0, 0],
};

// Camera preset positions: [position, target]
// position: [x, y, z], target: [x, y, z]
const CAMERA_PRESETS: Record<string, { position: [number, number, number]; target: [number, number, number] }> = {
  overview: { position: [0, 3, 8], target: [0, 0, 0] },
  engine_bay: { position: [0, 3, 4], target: [0, 1, 0] },
  front: { position: [0, 1.5, 6], target: [0, 0.5, 0] },
  rear: { position: [0, 1.5, -6], target: [0, 0.5, 0] },
  underbody: { position: [0, -3, 0], target: [0, -0.5, 0] },
};

class ErrorBoundary extends React.Component<
  { fallback: ReactNode; children?: ReactNode },
  { hasError: boolean }
> {
  constructor(props: { fallback: ReactNode; children?: ReactNode }) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('Vehicle3DViewer error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback;
    }
    return this.props.children;
  }
}

interface GenericVehicleModelProps {
  highlightedRegions: Set<string>;
  selectedComponent: ComponentHighlight | null;
  onRegionClick: (region: string) => void;
}

function GenericVehicleModel({ highlightedRegions, selectedComponent, onRegionClick }: GenericVehicleModelProps) {
  return (
    <group>
      {Object.keys(REGION_POSITIONS).map((region) => {
        const isSelected = selectedComponent?.vehicle_region === region;
        return (
          <mesh
            key={region}
            onClick={() => onRegionClick?.(region)}
            userData={{ region }}
            position={REGION_POSITIONS[region as keyof typeof REGION_POSITIONS]}
          >
            <boxGeometry args={REGION_SIZES[region as keyof typeof REGION_SIZES]} />
            <meshStandardMaterial
              color={highlightedRegions.has(region) ? (isSelected ? 0xff8800 : 0xffff00) : REGION_COLORS[region as keyof typeof REGION_COLORS]}
              opacity={0.8}
              transparent
            />
          </mesh>
        );
      })}
    </group>
  );
}

interface CameraControlsProps {
  selectedComponent: ComponentHighlight | null;
  activePreset: string;
  controlsRef: React.RefObject<OrbitControlsImpl | null>;
}

function CameraControls({ selectedComponent, activePreset, controlsRef }: CameraControlsProps) {
  const { camera } = useThree();
  const isAnimatingRef = useRef(false);
  const lastPresetRef = useRef<string>(activePreset);
  const animationFrameRef = useRef<number | null>(null);

  const cancelAnimation = useCallback(() => {
    if (animationFrameRef.current !== null) {
      cancelAnimationFrame(animationFrameRef.current);
      animationFrameRef.current = null;
    }
    isAnimatingRef.current = false;
  }, []);

  useEffect(() => {
    return () => {
      cancelAnimation();
    };
  }, [cancelAnimation]);

  // Handle preset button changes
  useEffect(() => {
    if (activePreset === lastPresetRef.current || isAnimatingRef.current) return;
    
    const preset = CAMERA_PRESETS[activePreset];
    if (!preset) return;

    const orbitControls = controlsRef.current;
    if (!orbitControls) return;
    
    cancelAnimation();
    isAnimatingRef.current = true;
    lastPresetRef.current = activePreset;
    const startPos = camera.position.clone();
    const startTarget = orbitControls.target.clone();
    const endPos = new THREE.Vector3(...preset.position);
    const endTarget = new THREE.Vector3(...preset.target);

    const duration = 800; // ms
    const startTime = performance.now();

    const animate = (time: number) => {
      const elapsed = time - startTime;
      const progress = Math.min(elapsed / duration, 1);
      // Ease out cubic
      const eased = 1 - Math.pow(1 - progress, 3);

      camera.position.lerpVectors(startPos, endPos, eased);
      orbitControls.target.lerpVectors(startTarget, endTarget, eased);
      orbitControls.update();

      if (progress < 1) {
        animationFrameRef.current = requestAnimationFrame(animate);
      } else {
        isAnimatingRef.current = false;
        animationFrameRef.current = null;
      }
    };

    animationFrameRef.current = requestAnimationFrame(animate);
  }, [activePreset, camera, controlsRef, cancelAnimation]);

  // Auto-focus on selected component's region OR component-specific target
  useEffect(() => {
    if (!selectedComponent || isAnimatingRef.current) return;

    const componentId = selectedComponent.component_id;
    const componentTarget = getComponentCameraTarget(componentId);
    
    // Determine target: component-specific > region preset
    let targetPreset: { position: [number, number, number]; target: [number, number, number] } | null = null;
    
    if (componentTarget) {
      targetPreset = componentTarget;
    } else if (selectedComponent.vehicle_region) {
      targetPreset = CAMERA_PRESETS[selectedComponent.vehicle_region];
    }
    
    if (!targetPreset) return;

    const orbitControls = controlsRef.current;
    if (!orbitControls) return;
    
    cancelAnimation();
    isAnimatingRef.current = true;
    const startPos = camera.position.clone();
    const startTarget = orbitControls.target.clone();
    const endPos = new THREE.Vector3(...targetPreset.position);
    const endTarget = new THREE.Vector3(...targetPreset.target);

    const duration = 800; // ms
    const startTime = performance.now();

    const animate = (time: number) => {
      const elapsed = time - startTime;
      const progress = Math.min(elapsed / duration, 1);
      // Ease out cubic
      const eased = 1 - Math.pow(1 - progress, 3);

      camera.position.lerpVectors(startPos, endPos, eased);
      orbitControls.target.lerpVectors(startTarget, endTarget, eased);
      orbitControls.update();

      if (progress < 1) {
        animationFrameRef.current = requestAnimationFrame(animate);
      } else {
        isAnimatingRef.current = false;
        animationFrameRef.current = null;
      }
    };

    animationFrameRef.current = requestAnimationFrame(animate);
  }, [selectedComponent, camera, controlsRef, cancelAnimation]);

  // This component doesn't render anything - it just handles camera animation
  return null;
}

interface GLBSceneProps {
  modelAsset: string;
  highlightedComponents: ComponentHighlight[];
  selectedComponent: ComponentHighlight | null;
  onComponentSelect: (componentId: string) => void;
  onRegionClick: (region: string) => void;
  vehicleType: VehicleType;
  onLoadStateChange?: (state: 'loading' | 'loaded' | 'error' | 'no-meshes', detail?: string) => void;
}

function GLBScene({ modelAsset, highlightedComponents, selectedComponent, onComponentSelect, onRegionClick, vehicleType, onLoadStateChange }: GLBSceneProps) {
  const { scene } = useGLTF(modelAsset);
  const highlightMaterialsRef = React.useRef<Map<string, THREE.MeshStandardMaterial>>(new Map());
  const originalMaterialsRef = React.useRef<Map<THREE.Mesh, THREE.Material | THREE.Material[]>>(new Map());

  React.useEffect(() => {
    if (!scene) {
      console.warn(`[Vehicle3DViewer] GLB scene is null for ${modelAsset}`);
      onLoadStateChange?.('error', 'Scene is null');
      return;
    }

    let meshCount = 0;
    scene.traverse((object: THREE.Object3D) => {
      if (object instanceof THREE.Mesh) {
        meshCount++;
      }
    });

    if (meshCount === 0) {
      console.warn(`[Vehicle3DViewer] GLB loaded but contains no meshes: ${modelAsset}`);
      onLoadStateChange?.('no-meshes', 'Model contains no meshes');
    } else {
      console.log(`[Vehicle3DViewer] GLB loaded successfully: ${modelAsset} (${meshCount} meshes)`);
      onLoadStateChange?.('loaded');
    }
  }, [scene, modelAsset, onLoadStateChange]);

  if (!scene) {
    return null;
  }

  useFrame(() => {
    scene.traverse((object: THREE.Object3D) => {
      if (object instanceof THREE.Mesh) {
        const mesh = object as THREE.Mesh;
        const nodeName = mesh.name;
        
        let matchedComponent: ComponentHighlight | null = null;
        let isSelected = false;
        
        for (const component of highlightedComponents) {
          const nodeNames = resolveNodeNamesForComponent(component, vehicleType);
          if (nodeNames.includes(nodeName)) {
            matchedComponent = component;
            isSelected = selectedComponent?.component_id === component.component_id;
            break;
          }
        }

        if (matchedComponent) {
          const region = matchedComponent.vehicle_region;
          const materialKey = region ?? matchedComponent.component_id;
          if (!originalMaterialsRef.current.has(mesh)) {
            originalMaterialsRef.current.set(mesh, mesh.material);
          }
          let highlightMat = highlightMaterialsRef.current.get(materialKey);
          if (!highlightMat) {
            const isSelectedComp = isSelected;
            highlightMat = new THREE.MeshStandardMaterial({
              color: isSelectedComp ? 0xff8800 : 0xffff00,
              emissive: isSelectedComp ? 0x663300 : 0x444400,
              emissiveIntensity: isSelectedComp ? 0.8 : 0.5,
              transparent: true,
              opacity: 0.9,
            });
            highlightMaterialsRef.current.set(materialKey, highlightMat);
          }
          mesh.material = highlightMat;
          mesh.userData.region = region;
          mesh.userData.componentId = matchedComponent.component_id;
          mesh.userData.isSelected = isSelected;
        } else if (originalMaterialsRef.current.has(mesh)) {
          mesh.material = originalMaterialsRef.current.get(mesh)!;
          originalMaterialsRef.current.delete(mesh);
        }
      }
    });
  });

  const handleClick = (event: React.MouseEvent<THREE.Object3D<THREE.Object3DEventMap>, MouseEvent>) => {
    const target = event.currentTarget as THREE.Object3D;
    if (target instanceof THREE.Mesh) {
      const mesh = target as THREE.Mesh;
      const componentId = mesh.userData.componentId;
      const region = mesh.userData.region;
      if (componentId) {
        onComponentSelect(componentId);
      } else if (region) {
        onRegionClick(region);
      }
    }
  };

  return (
    <primitive object={scene} onClick={handleClick} dispose={null} />
  );
}

interface GLBModelWrapperProps {
  modelAsset: string;
  highlightedComponents: ComponentHighlight[];
  selectedComponent: ComponentHighlight | null;
  onComponentSelect: (componentId: string) => void;
  onRegionClick: (region: string) => void;
  vehicleType: VehicleType;
  onLoadStateChange?: (state: 'loading' | 'loaded' | 'error' | 'no-meshes', detail?: string) => void;
}

function GLBModelWrapper({ modelAsset, highlightedComponents, selectedComponent, onComponentSelect, onRegionClick, vehicleType, onLoadStateChange }: GLBModelWrapperProps) {
  const fallbackRegions = new Set(highlightedComponents.map(c => c.vehicle_region).filter((r): r is string => r !== undefined));
  return (
    <Suspense fallback={<GenericVehicleModel highlightedRegions={fallbackRegions} selectedComponent={selectedComponent} onRegionClick={onRegionClick} />}>
      <GLBScene modelAsset={modelAsset} highlightedComponents={highlightedComponents} selectedComponent={selectedComponent} onComponentSelect={onComponentSelect} onRegionClick={onRegionClick} vehicleType={vehicleType} onLoadStateChange={onLoadStateChange} />
    </Suspense>
  );
}

export function Vehicle3DViewer({
  vehicleType = 'sedan',
  highlightedComponents = [],
  selectedComponent = null,
  onComponentSelect,
  className = '',
  children,
}: Vehicle3DViewerProps) {
  const [loadState, setLoadState] = React.useState<'idle' | 'loading' | 'loaded' | 'error' | 'no-meshes'>('idle');
  const [loadError, setLoadError] = React.useState<string | null>(null);

  const handleLoadStateChange = useCallback((state: 'loading' | 'loaded' | 'error' | 'no-meshes', detail?: string) => {
    setLoadState(state);
    if (state === 'error' || state === 'no-meshes') {
      setLoadError(detail || 'Unknown error');
    } else {
      setLoadError(null);
    }
  }, []);

  const highlightedRegions = useMemo(() => {
    return new Set(
      highlightedComponents
        .map((c) => c.vehicle_region)
        .filter((region): region is string => region !== null && region !== undefined)
    );
  }, [highlightedComponents]);

  const handleRegionClick = (region: string) => {
    const component = highlightedComponents.find((c) => c.vehicle_region === region);
    onComponentSelect?.(component ?? null);
  };

  const handleComponentClick = (componentId: string) => {
    const component = highlightedComponents.find((c) => c.component_id === componentId);
    onComponentSelect?.(component ?? null);
  };

  const { modelAsset } = getVehicleTypeConfig(vehicleType);

  const [activePreset, setActivePreset] = React.useState<string>('overview');
  const controlsRef = useRef<OrbitControlsImpl | null>(null);

  const handlePresetChange = (preset: string) => {
    setActivePreset(preset);
  };

  const fallback = (
    <div className="text-center py-4">
      <p className="text-xs text-slate-500">3D preview unavailable</p>
      {loadState === 'error' && loadError && (
        <p className="text-[10px] text-slate-400 mt-1">
          Model failed to load: {loadError}
        </p>
      )}
      {loadState === 'no-meshes' && loadError && (
        <p className="text-[10px] text-slate-400 mt-1">
          Model loaded but contains no displayable parts: {loadError}
        </p>
      )}
      {loadState === 'idle' && (
        <p className="text-[10px] text-slate-400 mt-1">
          WebGL not supported or model loading failed
        </p>
      )}
    </div>
  );

  const isUsingFallback = !modelAsset && highlightedComponents.length > 0;

  return (
    <div
      className={[
        'flex flex-col items-center justify-center rounded-lg border border-dashed border-slate-300 bg-slate-50 p-3 sm:p-4 text-center sm:text-left',
        className,
      ].join(' ')}
    >
      <div className="w-full">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1 sm:gap-3">
          <div>
            <div className="text-sm font-medium text-slate-500">3D Vehicle Visualization</div>
            <div className="mt-1 text-xs text-slate-400">
              <span className="font-medium">Vehicle type: {vehicleType}</span>
              {modelAsset && (
                <span className="ml-2 text-[10px] text-slate-400">
                  ({modelAsset})
                </span>
              )}
            </div>
          </div>
          {isUsingFallback && (
            <span className="inline-flex items-center rounded-md bg-amber-50 px-2 py-1 text-xs font-medium text-amber-700 ring-1 ring-inset ring-amber-700/10">
              Fallback view
            </span>
          )}
        </div>
      </div>

      <div className="mt-3 w-full">
        <ErrorBoundary fallback={fallback}>
          <Suspense fallback={
            <div className="flex items-center justify-center rounded-lg border border-dashed border-slate-200 bg-white p-4 sm:p-6">
              <div className="flex items-center gap-3">
                <svg className="h-5 w-5 animate-spin text-brand-600" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                <span className="text-sm text-slate-600">Loading 3D model...</span>
              </div>
            </div>
          }>
            <div className="w-full overflow-hidden rounded-md">
              <Canvas camera={{ position: [0, 3, 8], fov: 45 }} style={{ height: 220, width: '100%' }}>
                <OrbitControls ref={controlsRef} enableZoom={true} enablePan={true} enableRotate={true} minDistance={3} maxDistance={15} />
                <ambientLight intensity={0.5} />
                <directionalLight position={[5, 5, 5]} intensity={0.8} />

                {modelAsset ? (
                  <GLBModelWrapper
                    modelAsset={modelAsset}
                    highlightedComponents={highlightedComponents}
                    selectedComponent={selectedComponent}
                    onComponentSelect={handleComponentClick}
                    onRegionClick={handleRegionClick}
                    vehicleType={vehicleType}
                    onLoadStateChange={handleLoadStateChange}
                  />
                ) : (
                  <GenericVehicleModel highlightedRegions={highlightedRegions} selectedComponent={selectedComponent} onRegionClick={handleRegionClick} />
                )}
                
                <CameraControls selectedComponent={selectedComponent} activePreset={activePreset} controlsRef={controlsRef} />
              </Canvas>
            </div>
          </Suspense>
        </ErrorBoundary>
      </div>

      {/* Camera Presets */}
      <div className="mt-3 w-full">
        <p className="text-xs font-medium uppercase tracking-wider text-slate-500 mb-1.5">Camera</p>
        <div className="flex flex-wrap gap-1.5 sm:gap-2 justify-center">
          {Object.keys(CAMERA_PRESETS).map((preset) => (
            <button
              key={preset}
              type="button"
              onClick={() => handlePresetChange(preset)}
              className={[
                'rounded-md border px-2.5 py-2 text-xs transition-colors min-w-[44px] min-h-[44px]',
                activePreset === preset
                  ? 'border-brand-500 bg-brand-50 text-brand-700'
                  : 'border-slate-200 bg-white text-slate-600 hover:bg-slate-50',
              ].join(' ')}
              aria-label={`Camera preset ${preset}`}
            >
              {preset.charAt(0).toUpperCase() + preset.slice(1).replace('_', ' ')}
            </button>
          ))}
          <button
            type="button"
            onClick={() => handlePresetChange('overview')}
            className={[
              'rounded-md border px-2.5 py-2 text-xs transition-colors min-w-[44px] min-h-[44px]',
              'border-slate-200 bg-white text-slate-600 hover:bg-slate-50',
            ].join(' ')}
            aria-label="Reset camera to overview"
          >
            Reset
          </button>
        </div>
      </div>

      {highlightedComponents.length > 0 && (
        <div className="mt-3 w-full">
          <p className="text-xs font-medium uppercase tracking-wider text-slate-500 mb-1.5">Highlighted</p>
          <div className="flex flex-wrap gap-1.5 sm:gap-2">
            {highlightedComponents.map((c) => (
              <button
                key={c.component_id}
                type="button"
                onClick={() => onComponentSelect?.(c)}
                className={[
                  'rounded-md border px-2.5 py-2 text-xs transition-colors min-w-[44px] min-h-[44px]',
                  selectedComponent?.component_id === c.component_id
                    ? 'border-brand-500 bg-brand-50 text-brand-700'
                    : 'border-slate-200 bg-white text-slate-600 hover:bg-slate-50',
                ].join(' ')}
              >
                {c.component_id.replace(/_/g, ' ')}
              </button>
            ))}
          </div>
        </div>
      )}

      {selectedComponent && (
        <div className="mt-2 flex items-center gap-2 text-xs text-brand-700">
          <span className="inline-flex h-2 w-2 shrink-0 rounded-full bg-brand-500" aria-hidden="true" />
          <span className="font-medium">Selected: {selectedComponent.component_id.replace(/_/g, ' ')}</span>
        </div>
      )}

      {selectedComponent && selectedComponent.safety_tier && (
        <div className="mt-3 w-full">
          <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
            <div className="flex items-start gap-2">
              <div className={[
                'flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center',
                SAFETY_TIER_COLORS[selectedComponent.safety_tier] || SAFETY_TIER_COLORS.default,
              ].join(' ')}>
                <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  {selectedComponent.safety_tier === 'immediate_professional' && (
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                  )}
                  {selectedComponent.safety_tier === 'mechanic_recommended' && (
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                  )}
                  {selectedComponent.safety_tier === 'diy_repair' && (
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  )}
                  {selectedComponent.safety_tier === 'diy_inspection' && (
                    <>
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                    </>
                  )}
                </svg>
              </div>
              <div className="flex-1 min-w-0">
                <p className={[
                  'font-medium text-sm',
                  SAFETY_TIER_COLORS[selectedComponent.safety_tier] ? SAFETY_TIER_COLORS[selectedComponent.safety_tier].replace('bg-', 'text-') : 'text-slate-600',
                ].join(' ')}>
                  {selectedComponent.safety_tier_label || SAFETY_TIER_LABELS[selectedComponent.safety_tier] || 'Unknown safety tier'}
                </p>
                <p className="mt-1 text-sm text-slate-600">
                  {selectedComponent.safety_tier_description || SAFETY_TIER_ACTIONS[selectedComponent.safety_tier] || 'No safety guidance available.'}
                </p>
                {selectedComponent.safety_tier_reasoning && selectedComponent.safety_tier_reasoning.length > 0 && (
                  <div className="mt-2">
                    <p className="text-xs font-medium text-slate-500">Why:</p>
                    <ul className="mt-1 list-disc space-y-1 pl-4 text-xs text-slate-500">
                      {selectedComponent.safety_tier_reasoning.map((reason, idx) => (
                        <li key={idx}>{reason}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {children}
      <div className="mt-3 text-[10px] text-slate-400">
        Three.js renderer active
      </div>
    </div>
  );
}