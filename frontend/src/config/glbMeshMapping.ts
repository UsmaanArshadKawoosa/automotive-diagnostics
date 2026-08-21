export type VehicleRegion =
  | 'engine_bay'
  | 'intake'
  | 'exhaust'
  | 'fuel_tank'
  | 'transmission'
  | 'chassis'
  | 'underbody';

export interface GLBMeshMapping {
  region: VehicleRegion;
  nodeNames: string[];
  fallbackColor: number;
}

export const DEFAULT_GLB_MESH_MAPPING: GLBMeshMapping[] = [
  {
    region: 'engine_bay',
    nodeNames: ['body'],
    fallbackColor: 0x808080,
  },
  {
    region: 'intake',
    nodeNames: ['body'],
    fallbackColor: 0x654321,
  },
  {
    region: 'exhaust',
    nodeNames: ['body'],
    fallbackColor: 0x2f2f2f,
  },
  {
    region: 'fuel_tank',
    nodeNames: ['body'],
    fallbackColor: 0x000080,
  },
  {
    region: 'transmission',
    nodeNames: ['body'],
    fallbackColor: 0x8b4513,
  },
  {
    region: 'chassis',
    nodeNames: ['body'],
    fallbackColor: 0x2f4f4f,
  },
  {
    region: 'underbody',
    nodeNames: ['body'],
    fallbackColor: 0x4b4b4b,
  },
];

export type VehicleType = 'hatchback' | 'sedan' | 'suv' | 'pickup' | 'van';

export const VEHICLE_SPECIFIC_MESH_MAPPINGS: Partial<Record<VehicleType, GLBMeshMapping[]>> = {
  sedan: [
    {
      region: 'engine_bay',
      nodeNames: ['Engine', 'BodyHoodUnder', 'BodyHoodInterior01', 'BodyHoodInterior02', 'BodyHoodTopgrill'],
      fallbackColor: 0x808080,
    },
    {
      region: 'chassis',
      nodeNames: ['BodyUnderside', 'Axles'],
      fallbackColor: 0x2f4f4f,
    },
    {
      region: 'exhaust',
      nodeNames: ['BodyUnderside'],
      fallbackColor: 0x2f2f2f,
    },
    {
      region: 'underbody',
      nodeNames: ['BodyUnderside'],
      fallbackColor: 0x4b4b4b,
    },
  ],
  // Other vehicle types use the default generic body+wheels structure
  // Future detailed models can override specific regions here
};

// --- Component-level mapping ---

export interface ComponentMeshMapping {
  componentId: string;
  nodeNames: string[];
}

export const DEFAULT_COMPONENT_MESH_MAPPING: ComponentMeshMapping[] = [
  // Wheel/brake components that map to actual wheel meshes in the GLBs
  { componentId: 'front_brake_rotor', nodeNames: ['wheel-front-right', 'wheel-front-left'] },
  { componentId: 'rear_brake_rotor', nodeNames: ['wheel-back-right', 'wheel-back-left'] },
  { componentId: 'front_brake_caliper', nodeNames: ['wheel-front-right', 'wheel-front-left'] },
  { componentId: 'rear_brake_caliper', nodeNames: ['wheel-back-right', 'wheel-back-left'] },
  { componentId: 'front_brake_pad', nodeNames: ['wheel-front-right', 'wheel-front-left'] },
  { componentId: 'rear_brake_pad', nodeNames: ['wheel-back-right', 'wheel-back-left'] },
  { componentId: 'front_wheel_bearing', nodeNames: ['wheel-front-right', 'wheel-front-left'] },
  { componentId: 'rear_wheel_bearing', nodeNames: ['wheel-back-right', 'wheel-back-left'] },
  { componentId: 'front_wheel_hub', nodeNames: ['wheel-front-right', 'wheel-front-left'] },
  { componentId: 'rear_wheel_hub', nodeNames: ['wheel-back-right', 'wheel-back-left'] },
  { componentId: 'front_tire', nodeNames: ['wheel-front-right', 'wheel-front-left'] },
  { componentId: 'rear_tire', nodeNames: ['wheel-back-right', 'wheel-back-left'] },
  { componentId: 'front_wheel', nodeNames: ['wheel-front-right', 'wheel-front-left'] },
  { componentId: 'rear_wheel', nodeNames: ['wheel-back-right', 'wheel-back-left'] },
  { componentId: 'brake_disc_front', nodeNames: ['wheel-front-right', 'wheel-front-left'] },
  { componentId: 'brake_disc_rear', nodeNames: ['wheel-back-right', 'wheel-back-left'] },
  { componentId: 'brake_rotor_front', nodeNames: ['wheel-front-right', 'wheel-front-left'] },
  { componentId: 'brake_rotor_rear', nodeNames: ['wheel-back-right', 'wheel-back-left'] },
];

export const VEHICLE_SPECIFIC_COMPONENT_MAPPINGS: Partial<Record<VehicleType, ComponentMeshMapping[]>> = {
  sedan: [
    // Engine
    { componentId: 'engine', nodeNames: ['Engine'] },
    // Brake discs (mapped to specific brake disc meshes in CarConcept)
    { componentId: 'front_brake_rotor', nodeNames: ['WheelFrontLBrakeDisc', 'WheelFrontRBrakeDisc'] },
    { componentId: 'front_brake_caliper', nodeNames: ['WheelFrontLBrakeDisc', 'WheelFrontRBrakeDisc'] },
    { componentId: 'front_brake_pad', nodeNames: ['WheelFrontLBrakePad', 'WheelFrontRBrakePad'] },
    { componentId: 'rear_brake_rotor', nodeNames: ['WheelRearLBrakeDisc', 'WheelRearRBrakeDisc'] },
    { componentId: 'rear_brake_caliper', nodeNames: ['WheelRearLBrakeDisc', 'WheelRearRBrakeDisc'] },
    { componentId: 'rear_brake_pad', nodeNames: ['WheelRearLBrakePad', 'WheelRearRBrakePad'] },
    // Wheels/rims
    { componentId: 'front_wheel', nodeNames: ['WheelFrontLRim', 'WheelFrontRRim'] },
    { componentId: 'rear_wheel', nodeNames: ['WheelRearLRim', 'WheelRearRRim'] },
    { componentId: 'front_tire', nodeNames: ['WheelFrontLRim', 'WheelFrontRRim'] },
    { componentId: 'rear_tire', nodeNames: ['WheelRearLRim', 'WheelRearRRim'] },
    // Engine bay components
    { componentId: 'air_filter', nodeNames: ['BodyHoodTopgrill'] },
    // Underbody/Chassis
    { componentId: 'axle', nodeNames: ['Axles'] },
  ],
  // Other vehicle types use the default generic wheel meshes
  // Future detailed models can override specific components here
};

export function getMeshMappingForRegion(
  region: VehicleRegion,
  vehicleType?: VehicleType
): GLBMeshMapping | undefined {
  if (vehicleType && VEHICLE_SPECIFIC_MESH_MAPPINGS[vehicleType]) {
    const specific = VEHICLE_SPECIFIC_MESH_MAPPINGS[vehicleType]!.find((m) => m.region === region);
    if (specific) return specific;
  }
  return DEFAULT_GLB_MESH_MAPPING.find((m) => m.region === region);
}

export function getNodeNamesForRegion(region: VehicleRegion, vehicleType?: VehicleType): string[] {
  const mapping = getMeshMappingForRegion(region, vehicleType);
  return mapping?.nodeNames ?? [];
}

export function getFallbackColorForRegion(region: VehicleRegion, vehicleType?: VehicleType): number {
  const mapping = getMeshMappingForRegion(region, vehicleType);
  return mapping?.fallbackColor ?? 0xcccccc;
}

export function getAllRegions(): VehicleRegion[] {
  return DEFAULT_GLB_MESH_MAPPING.map((m) => m.region);
}

// --- Component mapping helpers ---

export function getComponentMappingForVehicle(
  componentId: string,
  vehicleType?: VehicleType
): ComponentMeshMapping | undefined {
  if (vehicleType && VEHICLE_SPECIFIC_COMPONENT_MAPPINGS[vehicleType]) {
    const specific = VEHICLE_SPECIFIC_COMPONENT_MAPPINGS[vehicleType]!.find(
      (m) => m.componentId.toLowerCase() === componentId.toLowerCase()
    );
    if (specific) return specific;
  }
  return DEFAULT_COMPONENT_MESH_MAPPING.find(
    (m) => m.componentId.toLowerCase() === componentId.toLowerCase()
  );
}

export function getNodeNamesForComponent(componentId: string, vehicleType?: VehicleType): string[] {
  const mapping = getComponentMappingForVehicle(componentId, vehicleType);
  return mapping?.nodeNames ?? [];
}

/**
 * Resolves mesh node names for a highlighted component using a priority order:
 * 1. Vehicle-specific component mapping
 * 2. Default component mapping
 * 3. Vehicle-specific region mapping
 * 4. Default region mapping
 * 5. Empty array (no match)
 */
export function resolveNodeNamesForComponent(
  component: { component_id: string; vehicle_region?: string },
  vehicleType?: VehicleType
): string[] {
  // 1. Vehicle-specific component mapping
  if (vehicleType && VEHICLE_SPECIFIC_COMPONENT_MAPPINGS[vehicleType]) {
    const specific = VEHICLE_SPECIFIC_COMPONENT_MAPPINGS[vehicleType]!.find(
      (m) => m.componentId.toLowerCase() === component.component_id.toLowerCase()
    );
    if (specific && specific.nodeNames.length > 0) {
      return specific.nodeNames;
    }
  }

  // 2. Default component mapping
  const defaultComponent = DEFAULT_COMPONENT_MESH_MAPPING.find(
    (m) => m.componentId.toLowerCase() === component.component_id.toLowerCase()
  );
  if (defaultComponent && defaultComponent.nodeNames.length > 0) {
    return defaultComponent.nodeNames;
  }

  // 3. Vehicle-specific region mapping (fallback)
  if (component.vehicle_region) {
    if (vehicleType && VEHICLE_SPECIFIC_MESH_MAPPINGS[vehicleType]) {
      const specificRegion = VEHICLE_SPECIFIC_MESH_MAPPINGS[vehicleType]!.find(
        (m) => m.region === component.vehicle_region
      );
      if (specificRegion && specificRegion.nodeNames.length > 0) {
        return specificRegion.nodeNames;
      }
    }

    // 4. Default region mapping
    const defaultRegion = DEFAULT_GLB_MESH_MAPPING.find(
      (m) => m.region === component.vehicle_region
    );
    if (defaultRegion && defaultRegion.nodeNames.length > 0) {
      return defaultRegion.nodeNames;
    }
  }

  // 5. No match
  return [];
}

// Component-specific camera targets for when detailed meshes exist
export const COMPONENT_CAMERA_TARGETS: Record<string, { position: [number, number, number]; target: [number, number, number] }> = {
  // Engine
  'engine': { position: [0, 2, 4], target: [0, 1, 0] },
  
  // Front wheels - position camera to show front wheel area
  'front_brake_rotor': { position: [-2, 1.5, 3], target: [-0.5, 0.3, 0.8] },
  'front_brake_caliper': { position: [-2, 1.5, 3], target: [-0.5, 0.3, 0.8] },
  'front_brake_pad': { position: [-2, 1.5, 3], target: [-0.5, 0.3, 0.8] },
  'front_wheel_bearing': { position: [-2, 1.5, 3], target: [-0.5, 0.3, 0.8] },
  'front_wheel_hub': { position: [-2, 1.5, 3], target: [-0.5, 0.3, 0.8] },
  'front_tire': { position: [-2, 1.5, 3], target: [-0.5, 0.3, 0.8] },
  'front_wheel': { position: [-2, 1.5, 3], target: [-0.5, 0.3, 0.8] },
  'brake_disc_front': { position: [-2, 1.5, 3], target: [-0.5, 0.3, 0.8] },
  'brake_rotor_front': { position: [-2, 1.5, 3], target: [-0.5, 0.3, 0.8] },

  // Rear wheels
  'rear_brake_rotor': { position: [-2, 1.5, -3], target: [-0.5, 0.3, -0.8] },
  'rear_brake_caliper': { position: [-2, 1.5, -3], target: [-0.5, 0.3, -0.8] },
  'rear_brake_pad': { position: [-2, 1.5, -3], target: [-0.5, 0.3, -0.8] },
  'rear_wheel_bearing': { position: [-2, 1.5, -3], target: [-0.5, 0.3, -0.8] },
  'rear_wheel_hub': { position: [-2, 1.5, -3], target: [-0.5, 0.3, -0.8] },
  'rear_tire': { position: [-2, 1.5, -3], target: [-0.5, 0.3, -0.8] },
  'rear_wheel': { position: [-2, 1.5, -3], target: [-0.5, 0.3, -0.8] },
  'brake_disc_rear': { position: [-2, 1.5, -3], target: [-0.5, 0.3, -0.8] },
  'brake_rotor_rear': { position: [-2, 1.5, -3], target: [-0.5, 0.3, -0.8] },
};

export function getComponentCameraTarget(componentId: string): { position: [number, number, number]; target: [number, number, number] } | null {
  return COMPONENT_CAMERA_TARGETS[componentId] ?? null;
}