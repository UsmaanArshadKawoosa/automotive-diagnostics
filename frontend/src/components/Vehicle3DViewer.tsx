import type { ReactNode } from 'react';
import * as React from 'react';
import { Suspense } from 'react';
import { Canvas, useLoader } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import { GLTFLoader } from 'three-stdlib';
import { getVehicleTypeConfig } from '../config/vehicleTypes';

export type VehicleType = 'hatchback' | 'sedan' | 'suv' | 'pickup' | 'van';

export interface ComponentHighlight {
  component_id: string;
  system_category?: string;
  vehicle_region?: string;
}

export interface Vehicle3DViewerProps {
  vehicleType?: VehicleType;
  highlightedComponents?: ComponentHighlight[];
  selectedComponent?: ComponentHighlight | null;
  onComponentSelect?: (component: ComponentHighlight | null) => void;
  className?: string;
  children?: ReactNode;
}

// Define regions and their default colors
const REGION_COLORS: Record<string, number> = {
  engine_bay: 0x808080, // gray
  intake: 0x654321, // brown
  exhaust: 0x2f2f2f, // dark gray
  underbody: 0x4b4b4b, // medium dark gray
  fuel_tank: 0x000080, // navy
  transmission: 0x8b4513, // saddle brown
  chassis: 0x2f4f4f, // dark slate gray
  default: 0xcccccc, // light gray
};

// Size estimates for different regions (width, height, depth)
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

// Position offsets for different regions (x, y, z)
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

// Simple error boundary component for WebGL/GLB loading errors
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

// Custom hook to safely load GLTF models with error handling
function useSafeGLTF(url: string | null) {
  const gltf = useLoader(GLTFLoader, url ?? '');
  // In practice, we'd need better error handling, but useLoader suspends on error
  // For simplicity in this implementation, we rely on the error boundary
  // GLTF object contains scene, scenes, nodes, materials, etc.
  // We'll return the scene as root, or the gltf itself if no scene
  return { 
    root: gltf.scene || gltf, 
    nodes: {}, 
    materials: [] 
  };
}

// Simple procedural vehicle made of boxes grouped by region
function GenericVehicleModel({ 
  highlightedRegions,
  onRegionClick
}: GenericVehicleModelProps) {
  return (
    <group>
      {/* Engine Bay */}
      <mesh
        onClick={() => onRegionClick?.('engine_bay')}
        userData={{ region: 'engine_bay' }}
        position={REGION_POSITIONS.engine_bay}
      >
        <boxGeometry 
          args={REGION_SIZES.engine_bay} 
        />
        <meshStandardMaterial
          color={highlightedRegions.has('engine_bay') ? 0xffff00 : REGION_COLORS.engine_bay}
          opacity={0.8}
          transparent
        />
      </mesh>
      
      {/* Intake */}
      <mesh
        onClick={() => onRegionClick?.('intake')}
        userData={{ region: 'intake' }}
        position={REGION_POSITIONS.intake}
      >
        <boxGeometry 
          args={REGION_SIZES.intake} 
        />
        <meshStandardMaterial
          color={highlightedRegions.has('intake') ? 0xffff00 : REGION_COLORS.intake}
          opacity={0.8}
          transparent
        />
      </mesh>
      
      {/* Exhaust */}
      <mesh
        onClick={() => onRegionClick?.('exhaust')}
        userData={{ region: 'exhaust' }}
        position={REGION_POSITIONS.exhaust}
      >
        <boxGeometry 
          args={REGION_SIZES.exhaust} 
        />
        <meshStandardMaterial
          color={highlightedRegions.has('exhaust') ? 0xffff00 : REGION_COLORS.exhaust}
          opacity={0.8}
          transparent
        />
      </mesh>
      
      {/* Underbody */}
      <mesh
        onClick={() => onRegionClick?.('underbody')}
        userData={{ region: 'underbody' }}
        position={REGION_POSITIONS.underbody}
      >
        <boxGeometry 
          args={REGION_SIZES.underbody} 
        />
        <meshStandardMaterial
          color={highlightedRegions.has('underbody') ? 0xffff00 : REGION_COLORS.underbody}
          opacity={0.8}
          transparent
        />
      </mesh>
      
      {/* Fuel Tank */}
      <mesh
        onClick={() => onRegionClick?.('fuel_tank')}
        userData={{ region: 'fuel_tank' }}
        position={REGION_POSITIONS.fuel_tank}
      >
        <boxGeometry 
          args={REGION_SIZES.fuel_tank} 
        />
        <meshStandardMaterial
          color={highlightedRegions.has('fuel_tank') ? 0xffff00 : REGION_COLORS.fuel_tank}
          opacity={0.8}
          transparent
        />
      </mesh>
      
      {/* Transmission */}
      <mesh
        onClick={() => onRegionClick?.('transmission')}
        userData={{ region: 'transmission' }}
        position={REGION_POSITIONS.transmission}
      >
        <boxGeometry 
          args={REGION_SIZES.transmission} 
        />
        <meshStandardMaterial
          color={highlightedRegions.has('transmission') ? 0xffff00 : REGION_COLORS.transmission}
          opacity={0.8}
          transparent
        />
      </mesh>
      
      {/* Chassis */}
      <mesh
        onClick={() => onRegionClick?.('chassis')}
        userData={{ region: 'chassis' }}
        position={REGION_POSITIONS.chassis}
      >
        <boxGeometry 
          args={REGION_SIZES.chassis} 
        />
        <meshStandardMaterial
          color={highlightedRegions.has('chassis') ? 0xffff00 : REGION_COLORS.chassis}
          opacity={0.8}
          transparent
        />
      </mesh>
    </group>
  );
}

// Main Vehicle3DViewer component
export function Vehicle3DViewer({
  vehicleType = 'sedan',
  highlightedComponents = [],
  selectedComponent = null,
  onComponentSelect,
  className = '',
  children,
}: Vehicle3DViewerProps) {
  // Convert highlighted components to a set of regions for quick lookup
  const highlightedRegions = React.useMemo(() => {
    return new Set(
      highlightedComponents
        .map(c => c.vehicle_region)
        .filter((region): region is string => region !== null && region !== undefined)
    );
  }, [highlightedComponents]);
  
  // Handle region clicks from the 3D scene
  const handleRegionClick = (region: string) => {
    // Find the first highlighted component in this region
    const component = highlightedComponents.find(
      c => c.vehicle_region === region
    );
    onComponentSelect?.(component ?? null);
  };
  
  // Get vehicle type config
  const { modelAsset } = getVehicleTypeConfig(vehicleType);
  
  // Error boundary fallback content
  const fallback = (
    <div className="text-center py-4">
      <p className="text-xs text-slate-500">3D preview unavailable</p>
      <p className="text-[10px] text-slate-400">
        WebGL not supported or model loading failed
      </p>
    </div>
  );
  
  return (
    <div
      className={[
        'flex flex-col items-center justify-center rounded-lg border border-dashed border-slate-300 bg-slate-50 p-6 text-center',
        className,
      ].join(' ')}
    >
      <div className="text-sm font-medium text-slate-500">3D Vehicle Visualization</div>
      <div className="mt-1 text-xs text-slate-400">
        Vehicle type: {vehicleType}
      </div>
      
      {/* Error boundary for WebGL/GLB loading errors */}
      <ErrorBoundary fallback={fallback}>
        <Suspense fallback={<div className="text-xs text-slate-400">Loading 3D model...</div>}>
          <Canvas
            camera={{ position: [0, 3, 8], fov: 45 }}
            style={{ height: 240, width: '100%' }}
          >
            <OrbitControls 
              enableZoom={true} 
              enablePan={true} 
              enableRotate={true}
              minDistance={3}
              maxDistance={15}
            />
            <ambientLight intensity={0.5} />
            <directionalLight position={[5, 5, 5]} intensity={0.8} />
            
            {/* Try to load GLB model if available, otherwise use procedural model */}
            {modelAsset ? (
              <Suspense fallback={
                <GenericVehicleModel 
                  highlightedRegions={highlightedRegions} 
                  onRegionClick={handleRegionClick} 
                />
              }>
                <primitive object={useSafeGLTF(modelAsset).root} />
              </Suspense>
            ) : (
              <GenericVehicleModel 
                highlightedRegions={highlightedRegions} 
                onRegionClick={handleRegionClick} 
              />
            )}
          </Canvas>
        </Suspense>
      </ErrorBoundary>
      
      {/* Highlighted components legend (kept for test compatibility) */}
      {highlightedComponents.length > 0 && (
        <div className="mt-3 w-full text-left">
          <p className="text-xs font-medium uppercase tracking-wider text-slate-500 mb-1">Highlighted</p>
          <div className="flex flex-wrap gap-1.5">
            {highlightedComponents.map((c) => (
              <button
                key={c.component_id}
                type="button"
                onClick={() => onComponentSelect?.(c)}
                className={[
                  'rounded-md border px-2 py-1 text-xs transition-colors',
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
        <div className="mt-2 text-xs text-brand-600">
          Selected: {selectedComponent.component_id.replace(/_/g, ' ')}
        </div>
      )}
      
      {children}
      <div className="mt-3 text-[10px] text-slate-400">
        Three.js renderer active
      </div>
    </div>
  );
}

// Define the props interface for the generic vehicle model
interface GenericVehicleModelProps {
  highlightedRegions: Set<string>;
  onRegionClick: (region: string) => void;
}

// Helper component for the procedural vehicle model
// function genericVehicleModel({
//   highlightedRegions,
//   onRegionClick
// }: GenericVehicleModelProps) {
//   return <GenericVehicleModel 
//     highlightedRegions={highlightedRegions} 
//     onRegionClick={onRegionClick} 
//   >;
// }